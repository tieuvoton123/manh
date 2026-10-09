#include "chepgame_url_ui.hpp"
#include "pixel_font.hpp"
#include <algorithm>
#include <cctype>
#include <cstdio>

namespace chepgame {
namespace {
const int kWidth=1920;
const int kHeight=1080;
const int kCols=10;
const int kRows=5;
// One glyph per key; use X to insert, Square to delete and L1/R1 to move cursor.
const char kKeys[] = "1234567890"
                     "qwertyuiop"
                     "asdfghjkl:"
                     "zxcvbnm.-/"
                     "_-?=&%+@#~";
const SDL_Color bg = {28,7,8,255};
const SDL_Color panel = {65,14,12,255};
const SDL_Color red = {151,24,15,255};
const SDL_Color yellow = {255,220,73,255};
const SDL_Color white = {254,246,216,255};
const SDL_Color muted = {242,176,117,255};

void fill(SDL_Renderer* r,int x,int y,int w,int h,SDL_Color color) {
    SDL_SetRenderDrawColor(r,color.r,color.g,color.b,color.a);
    SDL_Rect box={x,y,w,h}; SDL_RenderFillRect(r,&box);
}

bool valid_url(const std::string& u) {
    if (!(u.compare(0,7,"http://")==0 || u.compare(0,8,"https://")==0)) return false;
    const size_t scheme_end=u.find("://");
    if (scheme_end==std::string::npos) return false;
    const size_t host_end=u.find_first_of("/?#",scheme_end+3);
    const std::string authority=u.substr(scheme_end+3,
        host_end==std::string::npos ? std::string::npos : host_end-(scheme_end+3));
    if (authority.empty() || authority.find('@')!=std::string::npos || u.size()>512) return false;
    if (u.find("..")!=std::string::npos && u.find("../")!=std::string::npos) return false;
    for(size_t i=0;i<u.size();++i) {
        const unsigned char c=static_cast<unsigned char>(u[i]);
        if (c<33 || c>126 || c=='"' || c=='\\' || c=='<' || c=='>') return false;
    }
    return true;
}
}

UrlEditor::UrlEditor(const std::string& url):text_(url),cursor_(url.size()),key_index_(0){}
void UrlEditor::reset(const std::string& url) {
    text_=url; cursor_=text_.size(); key_index_=0; error_.clear();
}
void UrlEditor::insert(char c) {
    if(text_.size()>=512) {error_="Đường dẫn quá dài";return;}
    if (c<33 || c>126 || c=='"' || c=='\\' || c=='<' || c=='>') return;
    text_.insert(cursor_,1,c); ++cursor_; error_.clear();
}
void UrlEditor::erase() {
    if(cursor_>0 && cursor_<=text_.size()) { text_.erase(cursor_-1,1); --cursor_; }
    error_.clear();
}
void UrlEditor::move_horizontal(int delta) {
    if(delta<0 && cursor_>0)--cursor_;
    else if(delta>0 && cursor_<text_.size())++cursor_;
}
bool UrlEditor::valid() const {return valid_url(text_);}
UrlAction UrlEditor::input(const SDL_Event& e) {
    int dx=0,dy=0;bool add=false,back=false,connect=false,cancel=false;
    if(e.type==SDL_TEXTINPUT) {
        for (const char* p=e.text.text; *p; ++p) insert(*p);
        return UrlNothing;
    }
    if(e.type==SDL_KEYDOWN) {
        if(e.key.repeat) return UrlNothing;
        const SDL_Keycode k=e.key.keysym.sym;
        dx=(k==SDLK_RIGHT)-(k==SDLK_LEFT);
        dy=(k==SDLK_DOWN)-(k==SDLK_UP);
        back=(k==SDLK_BACKSPACE || k==SDLK_DELETE);
        add=(k==SDLK_SPACE);
        connect=(k==SDLK_RETURN || k==SDLK_KP_ENTER);
        cancel=(k==SDLK_ESCAPE);
        if(k==SDLK_HOME)cursor_=0;
        if(k==SDLK_END)cursor_=text_.size();
        if(k==SDLK_PAGEUP)move_horizontal(-1);
        if(k==SDLK_PAGEDOWN)move_horizontal(1);
    } else if(e.type==SDL_JOYHATMOTION) {
        dx=((e.jhat.value&SDL_HAT_RIGHT)!=0)-((e.jhat.value&SDL_HAT_LEFT)!=0);
        dy=((e.jhat.value&SDL_HAT_DOWN)!=0)-((e.jhat.value&SDL_HAT_UP)!=0);
    } else if(e.type==SDL_JOYBUTTONDOWN) {
        // OpenOrbis SDL: Cross=0, Circle=1, Square=2, Triangle=3; shoulders 4,5.
        add=e.jbutton.button==0;
        cancel=e.jbutton.button==1;
        back=e.jbutton.button==2;
        connect=e.jbutton.button==3;
        if(e.jbutton.button==4)move_horizontal(-1);
        if(e.jbutton.button==5)move_horizontal(1);
    } else if(e.type==SDL_QUIT) return UrlCancel;
    if(dx)key_index_=(key_index_/kCols)*kCols+(key_index_%kCols+dx+kCols)%kCols;
    if(dy)key_index_=((key_index_/kCols+dy+kRows)%kRows)*kCols+key_index_%kCols;
    if(back)erase();
    if(add)insert(kKeys[key_index_]);
    if(connect) {
        if(!valid()) {error_="Địa chỉ chưa hợp lệ";return UrlNothing;}
        return UrlConnect;
    }
    if(cancel)return UrlCancel;
    return UrlNothing;
}

void UrlEditor::draw(SDL_Renderer* r) const {
    fill(r,0,0,kWidth,kHeight,bg);
    fill(r,0,0,kWidth,138,red);
    fill(r,0,135,kWidth,4,yellow);
    orbisshelf::draw_text(r,78,29,8,"CHEPGAME.NET",yellow);
    orbisshelf::draw_text(r,82,102,3,"BY SUPER MANH",white);

    orbisshelf::draw_text(r,88,187,6,"Kết nối máy chủ",white);
    orbisshelf::draw_text(r,90,251,3,"Nhập địa chỉ JSON của kho ứng dụng",muted);
    fill(r,85,315,1750,118,panel);
    fill(r,85,315,8,118,yellow);
    const size_t view=83;
    size_t first=cursor_>39?cursor_-39:0;
    if(first+view>text_.size() && text_.size()>view) first=text_.size()-view;
    const std::string snippet=text_.substr(first,view);
    orbisshelf::draw_text(r,107,352,3,snippet,white);
    const int cx=107+(int)(cursor_-first)*18;
    fill(r,cx,393,14,5,yellow);
    orbisshelf::draw_text(r,90,453,3,"X: Nhập    □: Xóa    L1/R1: Con trỏ",muted);

    for(int row=0;row<kRows;++row) for(int col=0;col<kCols;++col){
        const int i=row*kCols+col;
        const int x=110+col*169;
        const int y=515+row*73;
        fill(r,x,y,144,59,i==key_index_?yellow:panel);
        orbisshelf::draw_text(r,x+60,y+15,4,std::string(1,kKeys[i]),i==key_index_?bg:white);
    }
    fill(r,85,909,1750,116,red);
    orbisshelf::draw_text(r,112,936,4,"△  KẾT NỐI",yellow);
    orbisshelf::draw_text(r,112,990,3,"O  Bỏ qua",white);
    if(!error_.empty()) orbisshelf::draw_text(r,630,987,3,error_,yellow);
}
} // namespace chepgame
