"""Regression guard for PS4 SDL2 static archive undefined symbols."""
import pathlib
import re
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT.parent / '.github/workflows/build-chepgame-installer.yml'
SDL_REQUIRED = ('SDL2', 'SceVideoOut', 'SceAudioOut', 'ScePad')


class SDLLinkContractTests(unittest.TestCase):
    def test_linker_command_resolves_ps4_sdl_backends(self):
        # Dry run deliberately uses no OpenOrbis files.
        out = subprocess.run(
            ['make', '-n', 'OO_PS4_TOOLCHAIN=/virtual/openorbis',
             'LD=ld.lld-18', 'eboot.bin'],
            cwd=ROOT, check=True, capture_output=True, text=True,
        ).stdout
        matches = re.findall(r'-l(?:SDL2|SceVideoOut|SceAudioOut|ScePad)(?![\w])', out)
        self.assertEqual(matches, ['-l' + lib for lib in SDL_REQUIRED], out)

    def test_both_build_modes_have_same_sdl_platform_dependencies(self):
        for mode in ('0', '1'):
            with self.subTest(mode=mode):
                out = subprocess.run(
                    ['make', '-s', '--eval', 'show-libs:;@echo $(LIBS)',
                     'DIAGNOSTIC_ONLY=' + mode, 'show-libs'],
                    cwd=ROOT, check=True, capture_output=True, text=True,
                ).stdout
                for lib in SDL_REQUIRED:
                    self.assertIn('-l' + lib, out)
                self.assertLess(out.index('-lSDL2'), out.index('-lSceVideoOut'))
                self.assertLess(out.index('-lSDL2'), out.index('-lSceAudioOut'))
                self.assertLess(out.index('-lSDL2'), out.index('-lScePad'))

    def test_ci_has_sdk_dependency_preflight(self):
        yml = WORKFLOW.read_text()
        self.assertIn('Verify SDL2 platform link dependencies', yml)
        for lib in SDL_REQUIRED:
            self.assertIn(lib, yml)


if __name__ == '__main__':
    unittest.main()
