"""Regression tests for real PS4 downloader looping after 100%."""
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class DownloadStableV043Tests(unittest.TestCase):
    def test_completion_bar_button_latch_and_no_auto_reinstall(self):
        from tests.fixture_prepare import PrepareTests
        from prepare_native import prepare
        case=PrepareTests('test_output');case.setUp()
        try:
            prepare(case.source,ROOT,'http://192.168.1.6:8099/orbis/catalog.json')
            s=(case.source/'src/main.cpp').read_text(encoding='utf-8')
            m=(case.source/'Makefile').read_text(encoding='utf-8')
            for token in ('download_finished', 'completed_visible',
                          'chepgame_x_down', 'chepgame_enter_down',
                          'SDL_JOYBUTTONUP','SDL_KEYUP',
                          'if (chepgame_download_click && count && !busy)',
                          'PKG đã có trong /data/pkg – không tải lại',
                          'Tải hoàn tất – PKG sẵn sàng tại /data/pkg',
                          'Header PKG sai; giữ .downloading',
                          '100% – Đã lưu PKG vào HDD'):
                self.assertIn(token,s,token)
            self.assertIn('VERSION     := 0.45',m)
            self.assertIn('const bool done = status.find("Tải hoàn tất") == 0;',s)
            self.assertIn('if (false && remote_install',s)
            self.assertNotIn('"1 HDD BGFT","2 URL BGFT","3 Bato-style"',s)
            # Neither our normal successful completion nor a failed download
            # should automatically start a new job from worker code.
            job=s[s.index('    set_status(state, "Đang tải: "'):s.index('\nvoid chepgame_mode_log(',s.index('    set_status(state, "Đang tải: "'))]
            self.assertNotIn('start_job(',job)
        finally:
            case.tearDown()

    def test_actual_download_cpp_simulates_network_drop_and_content_length(self):
        from chepgame_download_stable_v043 import upgrade_http_text
        source=(ROOT/'tests/test_fast_download_v042.py').read_text(encoding='utf-8')
        pre=re.search(r"        pre=r'''\n(.*?)\n'''",source,re.S).group(1)
        main=re.search(r"        main=r'''\n(.*?)\n'''",source,re.S).group(1)
        old=(ROOT/'chepgame_fast_download_v042.py').read_text(encoding='utf-8')
        code=re.search(r"    fn=r'''(bool HttpClient::download\(.*?\n}\n)'''",old,re.S).group(1)
        code=upgrade_http_text(code)
        # Real SDK prototype is already used by upstream http_client.cpp;
        # mock the response length from local test data.
        pre=pre.replace('static int sceHttpGetAllResponseHeaders', '''static int sceHttpGetResponseContentLength(int,int* kind,size_t* length){
    if(responses[current].content_range=="NO_LENGTH")return -1;
    *kind=1;*length=responses[current].body.size();return 0;
}
static int sceHttpGetAllResponseHeaders''')
        scenarios=r'''
    // Unknown catalog size: use HTTP Content-Length, not first EOF alone.
    reset();add(200,full);assert(h.download(url,path.c_str(),nullptr,nullptr,received,err,"",0,""));
    assert(received==10 && slurp(path.c_str())==full);
    // A read failure AFTER the final byte is a completed file, not a retry loop.
    reset();add(200,full,"",10);assert(h.download(url,path.c_str(),nullptr,nullptr,received,err,"",10,""));
    assert(received==10 && response_at==1 && err.empty());
    // An origin with no verifiable total must never publish a partial PKG.
    reset();add(200,full,"NO_LENGTH");
    assert(!h.download(url,path.c_str(),nullptr,nullptr,received,err,"",0,""));
    assert(err.find("tổng dung lượng")!=string::npos);
    // Catalog total and HTTP total disagree. Reject BEFORE writing payload.
    reset();add(200,"ABCDEF");
    assert(!h.download(url,path.c_str(),nullptr,nullptr,received,err,"",10,""));
    assert(err.find("Dung lượng máy chủ")!=string::npos);
    // A new 10-byte file cannot suddenly be treated as a 6-byte PKG.
    reset();add(200,full);assert(h.download(url,path.c_str(),nullptr,nullptr,received,err,"",10,""));
    assert(received==10 && response_at==1);
    // Realistic resumed transfer >64 KiB, only append after the overlap matches.
    const string large(150000,'Z');
    const string large_url="http://localhost/large.pkg";
    { FILE* fp=fopen(path.c_str(),"wb");assert(fp);
      assert(fwrite(large.data(),1,120000,fp)==120000);fclose(fp);
      string meta=chepgame::resume_identity(large_url,150000,"");
      FILE* mf=fopen((path+".resume").c_str(),"wb");assert(mf);
      assert(fwrite(meta.data(),1,meta.size(),mf)==meta.size());fclose(mf);
    }
    reset();add(206,large.substr(54464),"bytes 54464-149999/150000");
    assert(h.download(large_url,path.c_str(),nullptr,nullptr,received,err,"",150000,""));
    assert(received==150000 && slurp(path.c_str())==large);
    assert(last_range=="bytes=54464-" && response_at==1);
'''
        main=main[:main.rindex('\n}')]+ '\n' + scenarios + main[main.rindex('\n}'):]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'sim.cpp').write_text(pre+'\nnamespace orbisshelf {\n'+code+'\n}\n'+main)
            result=subprocess.run(['g++','-std=c++11','-Wall','-Wextra','-Werror','-I',str(ROOT),str(p/'sim.cpp'),'-o',str(p/'sim')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run([str(p/'sim'),str(p)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr+result.stdout)

    def test_real_http_patch_not_only_fixture(self):
        from chepgame_fast_download_v042 import apply_http
        from chepgame_download_stable_v043 import upgrade_http_text
        source=(ROOT/'tests/test_fast_download_v042.py').read_text(encoding='utf-8')
        txt=re.search(r"        representative='''''''''(.*?)'''''''''",source,re.S).group(1)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'src').mkdir();f=p/'src/http_client.cpp';f.write_text(txt)
            apply_http(f,p,ROOT)
            updated=upgrade_http_text(f.read_text())
            self.assertIn('sceHttpGetResponseContentLength(handles.req',updated)
            self.assertIn('network_read_error',updated)
            self.assertIn('completed==expected_size',updated)
            self.assertIn('return false; // Disk/response error',updated)

if __name__=='__main__':unittest.main()
