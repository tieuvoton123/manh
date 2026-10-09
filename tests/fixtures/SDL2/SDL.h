#pragma once
#include <stdint.h>
typedef struct SDL_Renderer SDL_Renderer;
typedef struct { unsigned char r,g,b,a; } SDL_Color;
typedef struct { int x,y,w,h; } SDL_Rect;
typedef int SDL_Keycode;
typedef struct { SDL_Keycode sym; } SDL_Keysym;
typedef struct { uint8_t repeat; SDL_Keysym keysym; } SDL_KeyboardEvent;
typedef struct { char text[32]; } SDL_TextInputEvent;
typedef struct { uint8_t value; } SDL_JoyHatEvent;
typedef struct { uint8_t button; } SDL_JoyButtonEvent;
typedef struct { int type; SDL_KeyboardEvent key; SDL_TextInputEvent text; SDL_JoyHatEvent jhat; SDL_JoyButtonEvent jbutton; } SDL_Event;
#define SDL_TEXTINPUT 1
#define SDL_KEYDOWN 2
#define SDL_JOYHATMOTION 3
#define SDL_JOYBUTTONDOWN 4
#define SDL_QUIT 5
#define SDL_HAT_LEFT 8
#define SDL_HAT_RIGHT 2
#define SDL_HAT_UP 1
#define SDL_HAT_DOWN 4
#define SDLK_RIGHT 80
#define SDLK_LEFT 81
#define SDLK_DOWN 82
#define SDLK_UP 83
#define SDLK_BACKSPACE 84
#define SDLK_DELETE 85
#define SDLK_SPACE 86
#define SDLK_RETURN 87
#define SDLK_KP_ENTER 88
#define SDLK_ESCAPE 89
#define SDLK_HOME 90
#define SDLK_END 91
#define SDLK_PAGEUP 92
#define SDLK_PAGEDOWN 93
extern "C" int SDL_SetRenderDrawColor(SDL_Renderer*, unsigned char, unsigned char, unsigned char, unsigned char);
extern "C" int SDL_RenderFillRect(SDL_Renderer*, const SDL_Rect*);
