// Embedded *rasterized glyphs*, not font files; copyright and license in THIRD_PARTY.txt.
// Proportional advances and baseline bearings eliminate overlapping Vietnamese marks.
#include "font.hpp"
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <map>
#include <utility>
#include <vector>

namespace chepfont {
namespace {
struct GlyphRecord {
    uint32_t codepoint;
    uint8_t size;
    int16_t left,top;
    uint8_t w,h;
    uint16_t advance;
    uint32_t offset,length;
};
#include "glyph_data.inc"
std::map<uint64_t,SDL_Texture*> cache;
SDL_Renderer* owner=nullptr;
uint32_t next_cp(const std::string& s,size_t& pos) {
    if(pos>=s.size())return 0;
    unsigned char a=(unsigned char)s[pos++];
    if(a<0x80)return a;
    int n=0;uint32_t cp=0,minv=0;
    if((a&0xe0)==0xc0){n=1;cp=a&31;minv=128;}
    else if((a&0xf0)==0xe0){n=2;cp=a&15;minv=2048;}
    else if((a&0xf8)==0xf0){n=3;cp=a&7;minv=65536;}
    else return '?';
    if(pos+n>s.size()){pos=s.size();return '?';}
    for(int i=0;i<n;i++){
        unsigned char b=(unsigned char)s[pos];if((b&0xc0)!=0x80)return '?';
        pos++;cp=(cp<<6)|(b&63);
    }
    return cp>=minv&&cp<=0x10ffff&&!(cp>=0xd800&&cp<=0xdfff)?cp:'?';
}
int size_index(int sz) {return sz<=26?0:sz<=34?1:2;}
const GlyphRecord* lookup(uint32_t cp,int size) {
    const uint8_t actual=size_index(size)==0?26:size_index(size)==1?34:46;
    size_t lo=0,hi=sizeof(records)/sizeof(records[0]);
    const uint64_t key=((uint64_t)actual<<32)|cp;
    while(lo<hi){size_t mid=(lo+hi)/2;
        const uint64_t k=((uint64_t)records[mid].size<<32)|records[mid].codepoint;
        if(k<key)lo=mid+1;else hi=mid;
    }
    if(lo<sizeof(records)/sizeof(records[0]) && records[lo].codepoint==cp && records[lo].size==actual)
        return &records[lo];
    if(cp!=(uint32_t)'?')return lookup('?',size);
    return nullptr;
}
SDL_Texture* texture(SDL_Renderer* r,const GlyphRecord& g) {
    if(!r || !g.w || !g.h)return nullptr;
    if(owner!=r){clear();owner=r;}
    const uint64_t id=((uint64_t)g.size<<32)|g.codepoint;
    std::map<uint64_t,SDL_Texture*>::iterator it=cache.find(id);
    if(it!=cache.end())return it->second;
    std::vector<uint8_t> alpha((size_t)g.w*g.h,0);
    size_t at=0; const size_t limit=g.offset+g.length;
    for(size_t i=g.offset;i+1<limit && at<alpha.size();i+=2){
        const uint8_t n=encoded[i],value=encoded[i+1];
        for(unsigned j=0;j<n && at<alpha.size();++j)alpha[at++]=value;
    }
    SDL_Texture* tx=nullptr;
    if(at==alpha.size()){
        SDL_Surface* surf=SDL_CreateRGBSurfaceWithFormat(0,g.w,g.h,32,SDL_PIXELFORMAT_RGBA32);
        if(surf){
            if(!SDL_MUSTLOCK(surf)||SDL_LockSurface(surf)==0){
                for(int y=0;y<g.h;y++)for(int x=0;x<g.w;x++){
                    uint32_t* row=(uint32_t*)((uint8_t*)surf->pixels+y*surf->pitch);
                    row[x]=SDL_MapRGBA(surf->format,255,255,255,alpha[(size_t)y*g.w+x]);
                }
                if(SDL_MUSTLOCK(surf))SDL_UnlockSurface(surf);
                tx=SDL_CreateTextureFromSurface(r,surf);
                if(tx)SDL_SetTextureBlendMode(tx,SDL_BLENDMODE_BLEND);
            }
            SDL_FreeSurface(surf);
        }
    }
    cache[id]=tx;return tx;
}
}
void clear(){
    for(std::map<uint64_t,SDL_Texture*>::iterator it=cache.begin();it!=cache.end();++it) {
        if(it->second) SDL_DestroyTexture(it->second);
    }
    cache.clear();
    owner=nullptr;
}
int measure(const std::string& s,int sz){size_t pos=0;int w=0;while(pos<s.size()){
    const uint32_t cp=next_cp(s,pos);const GlyphRecord* g=lookup(cp,sz);if(g)w+=g->advance;
}return w;}
void draw(SDL_Renderer* r,int x,int y,int sz,const std::string& s,SDL_Color c){
    if(!r)return;
    const int font_size=size_index(sz)==0?26:size_index(sz)==1?34:46;
    int pen=x;size_t pos=0;
    while(pos<s.size()){
        const uint32_t cp=next_cp(s,pos);const GlyphRecord* g=lookup(cp,sz);
        if(!g)continue;
        SDL_Texture* tx=texture(r,*g);
        if(tx){SDL_SetTextureColorMod(tx,c.r,c.g,c.b);SDL_SetTextureAlphaMod(tx,c.a);
            SDL_Rect dest={pen+g->left,y+font_size+g->top,g->w,g->h};
            SDL_RenderCopy(r,tx,nullptr,&dest);
        }
        pen+=g->advance;
    }
}
std::string clip(const std::string& s,int sz,int max_width){
    if(measure(s,sz)<=max_width)return s;
    const std::string ell="...";
    std::string out;size_t p=0;
    while(p<s.size()){
        next_cp(s,p);
        std::string next=s.substr(0,p);
        if(measure(next+ell,sz)>max_width)break;
        out.swap(next);
    }
    return out+ell;
}
}
