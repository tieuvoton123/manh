#pragma once
#include <stdint.h>
typedef struct SDL_Window SDL_Window;
typedef struct SDL_Renderer SDL_Renderer;
typedef struct SDL_Texture SDL_Texture;
struct SDL_PixelFormat {};
typedef struct SDL_Surface {int pitch;void* pixels; SDL_PixelFormat* format;} SDL_Surface;
typedef struct SDL_Joystick SDL_Joystick;
typedef struct SDL_Rect {int x,y,w,h;} SDL_Rect;
typedef struct SDL_Color {uint8_t r,g,b,a;} SDL_Color;
typedef struct SDL_KeyboardEvent { struct {int sym;} keysym; uint8_t repeat;} SDL_KeyboardEvent;
typedef struct SDL_JoyHatEvent {uint8_t value;} SDL_JoyHatEvent;
typedef struct SDL_JoyButtonEvent {uint8_t button;} SDL_JoyButtonEvent;
typedef struct SDL_Event {uint32_t type;SDL_KeyboardEvent key;SDL_JoyHatEvent jhat;SDL_JoyButtonEvent jbutton;} SDL_Event;
#define SDL_INIT_VIDEO 1
#define SDL_INIT_JOYSTICK 2
#define SDL_WINDOWPOS_UNDEFINED 0
#define SDL_QUIT 256
#define SDL_KEYDOWN 768
#define SDL_JOYHATMOTION 1536
#define SDL_JOYBUTTONDOWN 1539
#define SDL_HAT_UP 1
#define SDL_HAT_DOWN 4
#define SDLK_UP 101
#define SDLK_DOWN 102
#define SDLK_RETURN 13
#define SDLK_ESCAPE 27
#define SDLK_r 114
#define SDLK_t 116
#define SDL_PIXELFORMAT_RGBA32 1
#define SDL_BLENDMODE_BLEND 1
#define SDL_MUSTLOCK(s) 0
int SDL_Init(unsigned); void SDL_Quit();
SDL_Window* SDL_CreateWindow(const char*,int,int,int,int,unsigned);
void SDL_DestroyWindow(SDL_Window*);
SDL_Surface* SDL_GetWindowSurface(SDL_Window*);
SDL_Renderer* SDL_CreateSoftwareRenderer(SDL_Surface*);
void SDL_DestroyRenderer(SDL_Renderer*);
SDL_Joystick* SDL_JoystickOpen(int); void SDL_JoystickClose(SDL_Joystick*);
int SDL_NumJoysticks();int SDL_PollEvent(SDL_Event*); void SDL_Delay(unsigned);uint32_t SDL_GetTicks();
int SDL_UpdateWindowSurface(SDL_Window*);
int SDL_SetRenderDrawColor(SDL_Renderer*,uint8_t,uint8_t,uint8_t,uint8_t);
int SDL_RenderFillRect(SDL_Renderer*,const SDL_Rect*);
SDL_Surface* SDL_CreateRGBSurfaceWithFormat(unsigned,int,int,int,unsigned);
int SDL_LockSurface(SDL_Surface*);void SDL_UnlockSurface(SDL_Surface*);
void SDL_FreeSurface(SDL_Surface*);
uint32_t SDL_MapRGBA(const SDL_PixelFormat*,uint8_t,uint8_t,uint8_t,uint8_t);
SDL_Texture* SDL_CreateTextureFromSurface(SDL_Renderer*,SDL_Surface*);
void SDL_DestroyTexture(SDL_Texture*);
int SDL_SetTextureBlendMode(SDL_Texture*,int);
int SDL_SetTextureColorMod(SDL_Texture*,uint8_t,uint8_t,uint8_t);
int SDL_SetTextureAlphaMod(SDL_Texture*,uint8_t);
int SDL_RenderCopy(SDL_Renderer*,SDL_Texture*,const SDL_Rect*,const SDL_Rect*);
