#pragma once
#include <SDL2/SDL.h>
#include <string>

namespace chepgame {
enum UrlAction { UrlNothing=0, UrlConnect=1, UrlCancel=2 };
class UrlEditor {
public:
    explicit UrlEditor(const std::string& url);
    void reset(const std::string& url);
    UrlAction input(const SDL_Event& event);
    void draw(SDL_Renderer* renderer) const;
    bool valid() const;
    const std::string& value() const { return text_; }
    void error(const std::string& value) { error_=value; }
private:
    void insert(char c);
    void erase();
    void move_horizontal(int delta);
    std::string text_;
    std::string error_;
    size_t cursor_;
    int key_index_;
};
}
