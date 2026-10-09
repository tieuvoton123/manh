import pathlib, shutil, subprocess, tempfile, unittest, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
class PS4SystemFontTests(unittest.TestCase):
    def test_license_assets(self):
        from fontTools.ttLib import TTFont
        for asset in ['noto_sans.ttf','noto_symbols2.ttf']:
            f=TTFont(str(ROOT/'assets'/asset))
            self.assertGreater(len(f['cmap'].tables),0)
        self.assertIn('SIL Open Font License',(ROOT/'NOTO_LICENSE.txt').read_text())
        self.assertNotIn('SVN-Amsi',(ROOT/'chepgame_system_font.cpp').read_text())
    def test_source_loading_and_glyph_fallback(self):
        text=(ROOT/'chepgame_system_font.cpp').read_text()
        for needle in ['/preinst/common/font/DFHEI5-SONY.ttf','/app0/assets/noto_sans.ttf',
                       '/app0/assets/noto_symbols2.ttf','stbtt_FindGlyphIndex',
                       'stbtt_GetCodepointKernAdvance','stbtt_GetCodepointHMetrics',
                       'stbtt_MakeCodepointBitmap','SDL_RenderCopy','font.log',
                       'SDL_SetTextureBlendMode','SDL_DestroyTexture']:
            self.assertIn(needle,text,needle)
    def test_true_type_renderer_cpp11_syntax(self):
        compiler=shutil.which('clang++') or shutil.which('g++')
        if not compiler:self.skipTest('C++ compiler absent')
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td);(p/'SDL2').mkdir()
            (p/'pixel_font.hpp').write_text('''#include <string>
#include <SDL2/SDL.h>
namespace orbisshelf {void draw_text(SDL_Renderer*,int,int,int,const std::string&,SDL_Color);int text_width(int,const std::string&);}
''')
            (p/'SDL2/SDL.h').write_text('''#pragma once
#include <stdint.h>
struct SDL_Renderer{};struct SDL_Texture{};struct SDL_PixelFormat{};
struct SDL_Color{uint8_t r,g,b,a;};struct SDL_Rect{int x,y,w,h;};
struct SDL_Surface{void* pixels;int pitch;SDL_PixelFormat* format;};
static const int SDL_PIXELFORMAT_RGBA32=1,SDL_BLENDMODE_BLEND=1;
inline int SDL_MUSTLOCK(SDL_Surface*){return 1;}
SDL_Surface* SDL_CreateRGBSurfaceWithFormat(uint32_t,int,int,int,uint32_t);
int SDL_LockSurface(SDL_Surface*);void SDL_UnlockSurface(SDL_Surface*);
uint32_t SDL_MapRGBA(SDL_PixelFormat*,uint8_t,uint8_t,uint8_t,uint8_t);
void SDL_FreeSurface(SDL_Surface*);
SDL_Texture* SDL_CreateTextureFromSurface(SDL_Renderer*,SDL_Surface*);
void SDL_DestroyTexture(SDL_Texture*);
int SDL_SetTextureBlendMode(SDL_Texture*,int);
int SDL_SetTextureColorMod(SDL_Texture*,uint8_t,uint8_t,uint8_t);
int SDL_SetTextureAlphaMod(SDL_Texture*,uint8_t);
int SDL_RenderCopy(SDL_Renderer*,SDL_Texture*,const SDL_Rect*,const SDL_Rect*);
''')
            # For host syntax only; actual stb_ttf.h is downloaded & hash-checked in Actions.
            shutil.copyfile(ROOT/'stb_truetype.h',p/'stb_truetype.h')
            f=p/'pixel_font.cpp';shutil.copyfile(ROOT/'chepgame_system_font.cpp',f)
            result=subprocess.run([compiler,'-std=c++11','-Wall','-Wextra','-fsyntax-only','-I',str(p),str(f)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
    def test_pinned_source_honors_hash(self):
        code=(ROOT/'fetch_stb_header.py').read_text()
        self.assertIn('blob ',code)
        self.assertIn('90a5c2e2b3fe563c98585294ca7a949876aec94c',code)
        workflow=(ROOT/'.github/workflows/build-ps4.yml').read_text()
        self.assertLess(workflow.index('Fetch verified TrueType renderer header'),workflow.index('Prepare ChepGame PS4 native sources'))
        self.assertIn('src/pixel_font.cpp',workflow)
