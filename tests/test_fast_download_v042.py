"""Real C++11 policy and mocked PS4 HTTP download behavior (no actual SDK needed)."""
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

class FastDownloadTests(unittest.TestCase):
    def test_generated_store_ui_and_flow(self):
        from tests.fixture_prepare import PrepareTests
        from prepare_native import prepare
        t=PrepareTests('test_output');t.setUp()
        try:
            prepare(t.source,ROOT,'http://192.168.1.6:8099/orbis/catalog.json')
            main=(t.source/'src/main.cpp').read_text()
            self.assertIn('v0.45',main)
            self.assertIn('if (false && remote_install',main)
            self.assertIn('http.download(item.pkg_url, staged_path.c_str()',main)
            self.assertIn('item.size_bytes, item.sha256)',main)
            self.assertIn('Header PKG sai; giữ .downloading',main)
            self.assertIn('magic[0]==0x7f',main)
            self.assertIn('Tải hoàn tất – PKG sẵn sàng',main)
            self.assertNotIn('"1 HDD BGFT","2 URL BGFT","3 Bato-style"',main)
        finally:t.tearDown()

    def test_resume_policy_compiles_and_validates_headers(self):
        cpp=r'''
#include "chepgame_resume_policy.hpp"
#include <cassert>
int main(){
 using namespace chepgame;
 uint64_t start=9,end=9,total=9;
 assert(read_content_range("bytes 655-999/1000",start,end,total));
 assert(start==655&&end==999&&total==1000);
 assert(!read_content_range("bytes 20-1/100",start,end,total));
 assert(!read_content_range("bytes 0-100/100",start,end,total));
 assert(!read_content_range("garbage",start,end,total));
 assert(range_valid(206,true,65536,"bytes 65536-99999/100000",100000,total));
 assert(total==100000);
 assert(!range_valid(206,true,65536,"bytes 0-99999/100000",100000,total));
 assert(!range_valid(206,true,65536,"bytes 65536-99999/100000",200000,total));
 assert(range_valid(200,true,65536,"",100000,total));
 assert(range_valid(200,false,0,"",100000,total));
 assert(!range_valid(206,false,0,"",100000,total));
 assert(overlap_from(100000)==34464 && overlap_from(42)==0);
 assert(resume_identity("a",2,"x") != resume_identity("b",2,"x"));
}
'''
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'t.cpp').write_text(cpp)
            exe=p/'a.out'
            r=subprocess.run(['g++','-std=c++11','-Wall','-Wextra','-Werror','-I',str(ROOT),str(p/'t.cpp'),'-o',str(exe)],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            r=subprocess.run([str(exe)],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)

    def test_upstream_http_patch_shapes(self):
        from chepgame_fast_download_v042 import apply_http
        representative='''''''''#include "http_client.hpp"
namespace orbisshelf {
namespace {
bool open_get(int http_context, const std::string& url, const std::string& bearer_token,
              RequestHandles& handles, int32_t& status, std::string& redirect, std::string& error) {
    const int send_result = sceHttpSendRequest(handles.req, 0, 0);
    return send_result >= 0;
}
bool open_final_get(int http_context, const std::string& initial_url, const std::string& bearer_token,
                    RequestHandles& handles, int32_t& status, std::string& final_url, std::string& error) {
    std::string url=initial_url,scoped_token=bearer_token,location;
    return open_get(http_context, url, scoped_token, handles, status, location, error);
}
}
bool HttpClient::download(const std::string&,const char*,ProgressCallback,void*,uint64_t&,
                          std::string&,const std::string&) {return false;}
} // namespace orbisshelf
'''''''''
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'src/http_client.cpp'; f.parent.mkdir(parents=True);f.write_text(representative)
            apply_http(f,Path(d),ROOT)
            out=f.read_text()
            self.assertIn('sceHttpAddRequestHeader(handles.req,"Range"',out)
            self.assertIn('open_get(http_context, url, scoped_token, range, handles',out)
            self.assertIn('overlap_checked',out)
            self.assertIn('lstat(metadata_path.c_str()',out)
            self.assertTrue((Path(d)/'src/chepgame_resume_policy.hpp').is_file())

    def test_real_download_function_simulated_ps4_network(self):
        patch=(ROOT/'chepgame_fast_download_v042.py').read_text()
        fragment=re.search(r"    fn=r'''(bool HttpClient::download\(.*?\n}\n)'''",patch,re.S)
        self.assertIsNotNone(fragment)
        impl=fragment.group(1)
        pre=r'''
#include "chepgame_resume_policy.hpp"
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <algorithm>
#include <sys/stat.h>
#include <unistd.h>
#include <cassert>
#include <cstdlib>
using std::string;
struct MockResponse {int status;string body;string content_range;int failure_after;};
static std::vector<MockResponse> responses;
static int current=-1;
static int response_at=0;
static int response_pos=0;
static string last_range;
static int c_open=0;
struct RequestHandles {int req;RequestHandles():req(-1){}};
static void close_request(RequestHandles&){}
static bool header_value(const char*,size_t,const char*,std::string& value){
    if(current<0)return false;
    value=responses[current].content_range;
    return !value.empty();
}
static bool open_final_get(int,const string&,const string&,RequestHandles& h,int32_t& status,string& final_url,string& error,const string& range){
    if(response_at>=(int)responses.size()){error="unexpected network attempt";return false;}
    current=response_at++; response_pos=0;
    status=responses[current].status;
    last_range=range;h.req=current;final_url="http://localhost/file.pkg";
    ++c_open;return true;
}
static int sceHttpGetAllResponseHeaders(int,char** data,size_t* n){static char dummy='a';*data=&dummy;*n=1;return 0;}
static int sceHttpReadData(int,void* dst,uint32_t cap){
    const MockResponse& r=responses[current];
    if(r.failure_after>=0 && response_pos>=r.failure_after)return -1;
    if(response_pos>=(int)r.body.size())return 0;
    const int n=std::min((int)cap,(int)r.body.size()-response_pos);
    const int allowed = r.failure_after<0?n:std::min(n,r.failure_after-response_pos);
    if(allowed<=0)return -1;
    memcpy(dst,r.body.data()+response_pos,allowed);response_pos+=allowed;return allowed;
}
static int32_t sceKernelUsleep(uint32_t){return 0;}
static std::string status_error(int s){return "HTTP " + std::to_string(s);}
namespace orbisshelf {
typedef void(*ProgressCallback)(uint64_t,uint64_t,void*);
struct HttpClient {
    int http_context_=1;
    bool download(const std::string&, const char*,ProgressCallback,void*,uint64_t&,std::string&,const std::string&,uint64_t,const std::string&);
};
}
'''
        main=r'''
static void add(int status,const string& body,const string& range="",int fail=-1){responses.push_back({status,body,range,fail});}
static string slurp(const char* p){FILE* f=fopen(p,"rb");if(!f)return "";string s;char buf[100];size_t n=0;while((n=fread(buf,1,sizeof(buf),f))>0)s.append(buf,n);fclose(f);return s;}
static void reset(){responses.clear();current=-1;response_at=0;response_pos=0;last_range="";c_open=0;}
static void seed(const char* path,const string& text,const string& url,const string& sha=""){
 FILE* f=fopen(path,"wb");assert(f);fwrite(text.data(),1,text.size(),f);fclose(f);
 string meta=chepgame::resume_identity(url,10,sha);string mp=string(path)+".resume";
 f=fopen(mp.c_str(),"wb");assert(f);fwrite(meta.data(),1,meta.size(),f);fclose(f);
}
int main(int argc,char** argv){
    assert(argc==2);string dir=argv[1],url="http://localhost/file.pkg";
    const string path=dir+"/game.pkg.downloading";
    const string full="ABCDEFGHIJ";
    orbisshelf::HttpClient h;uint64_t received=0;string err;
    reset(); add(200,full,"",4);add(206,full,"bytes 0-9/10");
    assert(h.download(url,path.c_str(),nullptr,nullptr,received,err,"",10,""));
    assert(received==10&&slurp(path.c_str())==full&&response_at==2);
    // Persisted partial state: resume with byte overlap check.
    reset();seed(path.c_str(),"ABCDEF",url);
    add(206,full,"bytes 0-9/10");
    assert(h.download(url,path.c_str(),nullptr,nullptr,received,err,"",10,""));
    assert(received==10&&slurp(path.c_str())==full);
    // Range ignored: a full 200 must overwrite, not append.
    reset();seed(path.c_str(),"ABCDEF",url);
    add(200,full);
    assert(h.download(url,path.c_str(),nullptr,nullptr,received,err,"",10,""));
    assert(slurp(path.c_str())==full);
    // Remote changes in overlap -> clean full restart, no corruption spliced.
    reset();seed(path.c_str(),"ZZZZZZ",url);
    add(206,full,"bytes 0-9/10");add(200,full);
    assert(h.download(url,path.c_str(),nullptr,nullptr,received,err,"",10,""));
    assert(slurp(path.c_str())==full&&response_at==2);
    // Content-Range wrong offset rejected; staging retained for retry.
    reset();seed(path.c_str(),"ABCDEF",url);
    add(206,full,"bytes 2-9/10");
    assert(!h.download(url,path.c_str(),nullptr,nullptr,received,err,"",10,""));
    assert(slurp(path.c_str())=="ABCDEF");
    // New catalog identity -> no untrusted reuse of old bytes.
    reset();seed(path.c_str(),"ABCDEF",url);
    add(200,full);
    assert(h.download(url+"2",path.c_str(),nullptr,nullptr,received,err,"",10,""));
    assert(slurp(path.c_str())==full);
}
'''
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);source=d/'simulation.cpp'
            source.write_text(pre+'\nnamespace orbisshelf {\n'+impl+'\n}\n'+main)
            result=subprocess.run(['g++','-std=c++11','-Wall','-Wextra','-I',str(ROOT),str(source),'-o',str(d/'sim')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run([str(d/'sim'),str(d)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr+result.stdout)

if __name__=='__main__':unittest.main()
