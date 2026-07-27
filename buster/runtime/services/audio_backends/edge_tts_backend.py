from __future__ import annotations

import asyncio
import tempfile
import threading
from pathlib import Path
from typing import Any


class EdgeTTSBackend:
    """Edge-TTS synthesis with optional interruptible playback."""

    def __init__(
        self,
        voice: str = "en-US-GuyNeural",
        rate: str = "+0%",
        volume: str = "+0%",
    ):
        self.voice = voice
        self.rate = rate
        self.volume = volume

        self.last_error = ""
        self._stop_event = threading.Event()
        self._playback_lock = threading.RLock()
        self._playing = False

    @property
    def available(self) -> bool:
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            return False

    @property
    def playback_available(self) -> bool:
        for module_name in (
            "pygame",
            "playsound3",
            "playsound",
        ):
            try:
                __import__(module_name)
                return True
            except ImportError:
                continue

        return False

    @property
    def interruptible(self) -> bool:
        try:
            import pygame  # noqa: F401
            return True
        except ImportError:
            return False

    @property
    def playing(self) -> bool:
        return self._playing

    def status(self) -> dict[str, Any]:
        return {
            "status": (
                "ready"
                if self.available and self.playback_available
                else "not_configured"
            ),
            "available": self.available,
            "configured": (
                self.available
                and self.playback_available
            ),
            "playback_available": self.playback_available,
            "voice": self.voice,
            "playing": self._playing,
            "interruptible": self.interruptible,
            "last_error": self.last_error,
        }

    async def synthesize_async(
        self,
        text: str,
        output_file: str | Path,
        *,
        voice: str | None = None,
        rate: str | None = None,
        volume: str | None = None,
    ) -> Path:
        try:
            import edge_tts
        except ImportError as exc:
            raise RuntimeError(
                "edge-tts is not installed. "
                "Run: pip install edge-tts"
            ) from exc

        output = Path(output_file).expanduser().resolve()
        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice or self.voice,
                rate=rate or self.rate,
                volume=volume or self.volume,
            )
            await communicate.save(str(output))
            return output

        except Exception as exc:
            self.last_error = str(exc)
            raise

    def synthesize(
        self,
        text: str,
        output_file: str | Path | None = None,
        **kwargs: Any,
    ) -> Path:
        if output_file is None:
            output_file = (
                Path(tempfile.gettempdir())
                / "buster_edge_tts_output.mp3"
            )

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.synthesize_async(
                    text,
                    output_file,
                    **kwargs,
                )
            )

        result: list[Path] = []
        error: list[BaseException] = []

        def runner() -> None:
            try:
                result.append(
                    asyncio.run(
                        self.synthesize_async(
                            text,
                            output_file,
                            **kwargs,
                        )
                    )
                )
            except BaseException as exc:
                error.append(exc)

        thread = threading.Thread(
            target=runner,
            daemon=True,
            name="BusterEdgeTTSSynthesis",
        )
        thread.start()
        thread.join()

        if error:
            raise error[0]

        return result[0]

    def stop(self) -> bool:
        """Stop active pygame playback immediately."""
        self._stop_event.set()
        stopped = False

        try:
            import pygame

            if pygame.mixer.get_init():
                pygame.mixer.music.stop()

                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass

                stopped = True

        except ImportError:
            pass

        finally:
            self._playing = False

        return stopped

    def play(
        self,
        path: str | Path,
    ) -> dict[str, Any]:
        """
        Play audio inside Buster.

        pygame is preferred because it supports interruption.
        playsound3 and playsound are compatibility fallbacks.
        """
        audio_path = Path(path).expanduser().resolve()
        if not audio_path.exists():
            raise FileNotFoundError(audio_path)

        with self._playback_lock:
            self._stop_event.clear()
            self._playing = True

            try:
                try:
                    import pygame

                    if not pygame.mixer.get_init():
                        pygame.mixer.init()

                    pygame.mixer.music.load(
                        str(audio_path)
                    )
                    pygame.mixer.music.play()

                    while pygame.mixer.music.get_busy():
                        if self._stop_event.wait(0.025):
                            pygame.mixer.music.stop()
                            break

                    try:
                        pygame.mixer.music.unload()
                    except Exception:
                        pass

                    return {
                        "backend": "pygame",
                        "interrupted": (
                            self._stop_event.is_set()
                        ),
                    }

                except ImportError:
                    pass

                try:
                    from playsound3 import playsound

                    playsound(
                        str(audio_path),
                        block=True,
                    )
                    return {
                        "backend": "playsound3",
                        "interrupted": False,
                    }

                except ImportError:
                    pass

                try:
                    from playsound import playsound

                    playsound(
                        str(audio_path),
                        block=True,
                    )
                    return {
                        "backend": "playsound",
                        "interrupted": False,
                    }

                except ImportError as exc:
                    raise RuntimeError(
                        "No in-process MP3 playback backend is installed. "
                        "For interruptible playback run: pip install pygame"
                    ) from exc

            except Exception as exc:
                self.last_error = str(exc)
                raise

            finally:
                self._playing = False
