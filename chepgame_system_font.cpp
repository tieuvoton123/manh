// PS4 system TrueType font renderer, optional Noto Sans Unicode fallback (SIL OFL).
// Uses stb_truetype (public domain/MIT, fetched/pinned at build time) for real
// proportional glyph advances, kerning and antialiasing. No Sony font distributed.
#include "pixel_font.hpp"
#define STB_TRUETYPE_IMPLEMENTATION
#include "stb_truetype.h"
#include <SDL2/SDL.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>

namespace orbisshelf {
namespace {
struct Font {
    std::vector<unsigned char> data;
    stbtt_fontinfo info;
    bool ready;
    Font(): ready(false) { std::memset(&info,0,sizeof(info)); }
};
Font sony, fallback, symbols;
bool initialized=false;
bool font_from_path(Font& font,const char* path) {
    FILE* f=std::fopen(path,"rb");
    if (!f) return false;
    if (std::fseek(f,0,SEEK_END)!=0) {std::fclose(f);return false;}
    const long n=std::ftell(f);
    if (n<=0 || n>16*1024*1024 || std::fseek(f,0,SEEK_SET)!=0) {std::fclose(f);return false;}
    std::vector<unsigned char> bytes((size_t)n);
    const size_t got=std::fread(bytes.data(),1,(size_t)n,f);
    std::fclose(f);
    if (got!=(size_t)n) return false;
    // Includes TrueType collections (.ttc) when present; only trusted OS and bundled assets.
    int offset=stbtt_GetFontOffsetForIndex(bytes.data(),0);
    if (offset<0) return false;
    stbtt_fontinfo info;
    if (!stbtt_InitFont(&info,bytes.data(),offset)) return false;
    font.data.swap(bytes);
    // stbtt_fontinfo keeps pointers into supplied font buffer.
    font.info=info;
    font.info.data=font.data.data();
    font.ready=true;
    return true;
}
void init_fonts() {
    if (initialized) return;
    initialized=true;
    const char* system_paths[]={
        "/preinst/common/font/DFHEI5-SONY.ttf",
        "/system_ex/app/NPXS20113/bdjstack/lib/fonts/SCE-PS3-RD-R-LATIN.TTF"
    };
    const char* chosen="no Sony font accessible";
    for (size_t i=0;i<sizeof(system_paths)/sizeof(system_paths[0]);++i) {
        if (font_from_path(sony,system_paths[i])) {chosen=system_paths[i];break;}
    }
    bool symbol_ok=font_from_path(symbols,"/app0/assets/noto_symbols2.ttf");
    if (!symbol_ok) symbol_ok=font_from_path(symbols,"assets/noto_symbols2.ttf");
    bool fallback_ok=font_from_path(fallback,"/app0/assets/noto_sans.ttf");
    if (!fallback_ok) fallback_ok=font_from_path(fallback,"assets/noto_sans.ttf");
    FILE* log=std::fopen("/data/ChepGameStore/font.log","w");
    if (log) {
        std::fprintf(log,"system=%s\nfallback=%s\nsymbols=%s\n",chosen,
                     fallback_ok?"Noto Sans ready":"unavailable",
                     symbol_ok?"Noto Symbols ready":"unavailable");
        std::fclose(log);
    }
}
uint32_t next_utf8(const std::string& s,size_t& pos) {
    if(pos>=s.size())return 0;
    const unsigned char a=(unsigned char)s[pos++];
    if(a<128)return a;
    int n=0;uint32_t cp=0,minv=0;
    if((a&0xe0)==0xc0){n=1;cp=a&31;minv=128;}
    else if((a&0xf0)==0xe0){n=2;cp=a&15;minv=2048;}
    else if((a&0xf8)==0xf0){n=3;cp=a&7;minv=65536;}
    else return '?';
    if(pos+(size_t)n>s.size()){pos=s.size();return '?';}
    for(int i=0;i<n;++i){
        const unsigned char b=(unsigned char)s[pos];
        if((b&0xc0)!=0x80)return '?';
        ++pos;cp=(cp<<6)|(b&63);
    }
    return cp>=minv&&cp<=0x10ffff&&!(cp>=0xd800&&cp<=0xdfff)?cp:'?';
}
// Select one font for an entire string to preserve consistent visual weight.
// If Sony lacks *any* Vietnamese glyph, render this label fully in Noto Sans.
Font* choose_font(const std::string& text) {
    init_fonts();
    if (!sony.ready) return fallback.ready?&fallback:nullptr;
    size_t pos=0;
    while(pos<text.size()) {
        const uint32_t cp=next_utf8(text,pos);
        if(cp=='\n'||cp=='\r'||cp=='\t')continue;
        if(!stbtt_FindGlyphIndex(&sony.info,(int)cp))return fallback.ready?&fallback:&sony;
    }
    return &sony;
}
// Button legends may mix Noto Sans text and Noto Symbols glyphs.
Font* glyph_font(Font* base,uint32_t cp) {
    if(stbtt_FindGlyphIndex(&base->info,(int)cp))return base;
    if(symbols.ready && stbtt_FindGlyphIndex(&symbols.info,(int)cp))return &symbols;
    if(fallback.ready && stbtt_FindGlyphIndex(&fallback.info,(int)cp))return &fallback;
    return base;
}
int font_pixels(int scale){return std::max(9,std::min(64,scale*8));}
struct Glyph {
    SDL_Texture* texture;
    int x0,y0,w,h;
    Glyph():texture(nullptr),x0(0),y0(0),w(0),h(0){}
};
std::map<uint64_t,Glyph> glyph_cache;
SDL_Renderer* active_renderer=nullptr;
void reset_cache(SDL_Renderer* renderer) {
    if(active_renderer==renderer)return;
    for(std::map<uint64_t,Glyph>::iterator it=glyph_cache.begin();it!=glyph_cache.end();++it)
        if(it->second.texture)SDL_DestroyTexture(it->second.texture);
    glyph_cache.clear();active_renderer=renderer;
}
uint64_t glyph_key(Font* font,int pixel_height,uint32_t cp) {
    const uint64_t which=font==&sony?1ULL:font==&fallback?2ULL:3ULL;
    return (which<<56)|((uint64_t)pixel_height<<32)|cp;
}
Glyph& cached_glyph(SDL_Renderer* renderer, Font* font, int pixels,uint32_t cp,float unit_scale) {
    const uint64_t key=glyph_key(font,pixels,cp);
    std::map<uint64_t,Glyph>::iterator it=glyph_cache.find(key);
    if(it!=glyph_cache.end())return it->second;
    Glyph glyph;
    int x1=0,y1=0;
    stbtt_GetCodepointBitmapBox(&font->info,(int)cp,unit_scale,unit_scale,
                                 &glyph.x0,&glyph.y0,&x1,&y1);
    glyph.w=x1-glyph.x0;glyph.h=y1-glyph.y0;
    if(glyph.w>0&&glyph.h>0&&glyph.w<=128&&glyph.h<=128) {
        std::vector<unsigned char> coverage((size_t)glyph.w*glyph.h,0);
        stbtt_MakeCodepointBitmap(&font->info,coverage.data(),glyph.w,glyph.h,
                                 glyph.w,unit_scale,unit_scale,(int)cp);
        SDL_Surface* surface=SDL_CreateRGBSurfaceWithFormat(0,glyph.w,glyph.h,32,SDL_PIXELFORMAT_RGBA32);
        if(surface) {
            if(!SDL_MUSTLOCK(surface)||SDL_LockSurface(surface)==0) {
                for(int y=0;y<glyph.h;++y)for(int x=0;x<glyph.w;++x) {
                    uint32_t* row=(uint32_t*)((unsigned char*)surface->pixels+y*surface->pitch);
                    row[x]=SDL_MapRGBA(surface->format,255,255,255,coverage[(size_t)y*glyph.w+x]);
                }
                if(SDL_MUSTLOCK(surface)) SDL_UnlockSurface(surface);
                glyph.texture=SDL_CreateTextureFromSurface(renderer,surface);
                if(glyph.texture) SDL_SetTextureBlendMode(glyph.texture,SDL_BLENDMODE_BLEND);
            }
            SDL_FreeSurface(surface);
        }
    }
    return glyph_cache.insert(std::make_pair(key,glyph)).first->second;
}
}

int text_width(int scale,const std::string& text) {
    if(scale<=0)return 0;
    Font* font=choose_font(text);
    if(!font)return 0;
    const float unit=stbtt_ScaleForPixelHeight(&font->info,(float)font_pixels(scale));
    float pen=0.0f,maxpen=0.0f;
    uint32_t prev=0;Font* previous_font=nullptr;
    size_t pos=0;
    while(pos<text.size()) {
        const uint32_t cp=next_utf8(text,pos);
        if(cp=='\n'){maxpen=std::max(maxpen,pen);pen=0;prev=0;previous_font=nullptr;continue;}
        if(cp=='\r')continue;
        if(cp=='\t'){pen+=4*font_pixels(scale)*0.35f;prev=0;previous_font=nullptr;continue;}
        Font* face=glyph_font(font,cp);
        const float metric_unit=face==font?unit:stbtt_ScaleForPixelHeight(&face->info,(float)font_pixels(scale));
        if(prev && previous_font==face)pen+=metric_unit*stbtt_GetCodepointKernAdvance(&face->info,(int)prev,(int)cp);
        int advance=0,l=0;
        stbtt_GetCodepointHMetrics(&face->info,(int)cp,&advance,&l);
        pen+=advance*metric_unit;prev=cp;previous_font=face;
    }
    return (int)std::ceil(std::max(maxpen,pen));
}
void draw_text(SDL_Renderer* renderer,int x,int y,int scale,const std::string& text,SDL_Color color) {
    if(!renderer||scale<=0||text.empty())return;
    Font* font=choose_font(text);
    if(!font)return;
    reset_cache(renderer);
    const int pixels=font_pixels(scale);
    const float unit=stbtt_ScaleForPixelHeight(&font->info,(float)pixels);
    int asc=0,des=0,gap=0;
    stbtt_GetFontVMetrics(&font->info,&asc,&des,&gap);
    const int baseline=y+(int)std::ceil(asc*unit);
    const int line_height=(int)std::ceil((asc-des+gap)*unit)+3;
    const int left=x;
    float pen=0.0f;
    int line_y=baseline;
    uint32_t prev=0;Font* previous_font=nullptr;
    size_t pos=0;
    while(pos<text.size()) {
        const uint32_t cp=next_utf8(text,pos);
        if(cp=='\n'){pen=0;prev=0;previous_font=nullptr;line_y+=line_height;continue;}
        if(cp=='\r')continue;
        if(cp=='\t'){pen+=4*pixels*0.35f;prev=0;previous_font=nullptr;continue;}
        Font* face=glyph_font(font,cp);
        const float metric_unit=face==font?unit:stbtt_ScaleForPixelHeight(&face->info,(float)pixels);
        if(prev && previous_font==face)pen+=metric_unit*stbtt_GetCodepointKernAdvance(&face->info,(int)prev,(int)cp);
        Glyph& glyph=cached_glyph(renderer,face,pixels,cp,metric_unit);
        if(glyph.texture) {
            SDL_SetTextureColorMod(glyph.texture,color.r,color.g,color.b);
            SDL_SetTextureAlphaMod(glyph.texture,color.a);
            SDL_Rect dest={left+(int)std::floor(pen+0.5f)+glyph.x0,
                          line_y+glyph.y0,glyph.w,glyph.h};
            SDL_RenderCopy(renderer,glyph.texture,nullptr,&dest);
        }
        int advance=0,l=0;
        stbtt_GetCodepointHMetrics(&face->info,(int)cp,&advance,&l);
        pen+=advance*metric_unit;prev=cp;previous_font=face;
    }
}
} // namespace orbisshelf
