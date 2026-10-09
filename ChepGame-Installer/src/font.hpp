#pragma once
#include <SDL2/SDL.h>
#include <string>
namespace chepfont {
void draw(SDL_Renderer* r,int x,int y,int size,const std::string& s,SDL_Color color);
int measure(const std::string& s,int size);
std::string clip(const std::string& s,int size,int max_width);
void clear();
}
