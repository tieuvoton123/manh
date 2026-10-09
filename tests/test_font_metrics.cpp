#include <string>
#include <cstdio>
namespace orbisshelf{int text_width(int,const std::string&);}
int main(){
  const int iii=orbisshelf::text_width(4,"iiii");
  const int www=orbisshelf::text_width(4,"WWWW");
  const int vi=orbisshelf::text_width(4,"Đã tải xong – Việt hóa");
  std::printf("font advance test: iiii=%d WWWW=%d Vietnamese=%d\n",iii,www,vi);
  return (iii>0 && www>iii && vi>100)?0:1;
}
