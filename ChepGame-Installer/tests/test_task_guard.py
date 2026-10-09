import pathlib
import subprocess
import tempfile
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
HARNESS=r'''
#include "task_guard.hpp"
#include "pkg_scan.hpp"
#include <cstdio>
#include <fstream>
#include <iostream>
#include <vector>
int main(int argc,char** argv){
 if(argc!=3)return 2;
 const std::string folder=argv[1], mode=argv[2];
 if(mode=="task"){
  auto path=folder+"/journal.txt";
  chepinstaller::PendingTask src;src.task_id=113;src.title_id="CUSA12345";src.filename="homebrew.pkg";
  if(!chepinstaller::write_pending_task(path,src))return 3;
  chepinstaller::PendingTask got;
  if(!chepinstaller::read_pending_task(path,got) || got.task_id!=113 ||
     got.title_id!="CUSA12345" || got.filename!="homebrew.pkg")return 4;
  if(!chepinstaller::acknowledge_pending_task(path))return 5;
  if(chepinstaller::read_pending_task(path,got))return 6;
  if(!chepinstaller::acknowledge_pending_task(path))return 7;
  return 0;
 }
 if(mode=="invalid"){
  chepinstaller::PendingTask src;src.task_id=1;src.title_id="CUSA12345";src.filename="../bad.pkg";
  if(chepinstaller::write_pending_task(folder+"/journal.txt",src))return 8;
  return 0;
 }
 if(mode=="modified"){
  std::string name=folder+"/homebrew.pkg";
  std::ofstream f(name,std::ios::binary);
  f.write("\x7f" "CNT",4);
  std::string zeros(8192,'\0');f.write(zeros.data(),zeros.size());f.close();
  std::vector<chepinstaller::PackageFile> files;std::string err;
  if(!chepinstaller::scan_packages(folder,files,err) || files.size()!=1)return 9;
  if(!chepinstaller::unchanged_package(files[0]))return 10;
  std::ofstream m(name,std::ios::binary|std::ios::app);m.put('!');m.close();
  if(chepinstaller::unchanged_package(files[0]))return 11;
  return 0;
 }
 return 12;
}
'''
class TaskGuardTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.work=tempfile.TemporaryDirectory()
  c=pathlib.Path(cls.work.name)/'test.cpp'
  c.write_text(HARNESS)
  cls.exe=pathlib.Path(cls.work.name)/'test'
  subprocess.run(['g++','-std=c++11','-Wall','-Wextra','-Werror',
    '-I'+str(ROOT/'src'),str(c),str(ROOT/'src/task_guard.cpp'),str(ROOT/'src/pkg_scan.cpp'),
    '-o',str(cls.exe)],check=True,capture_output=True,text=True)
 @classmethod
 def tearDownClass(cls):cls.work.cleanup()
 def test_pending_survives_restart_and_explicit_ack_removes_only_journal(self):
  with tempfile.TemporaryDirectory() as p:
   pathlib.Path(p,'my_game.pkg').write_text('MY GAME DATA')
   subprocess.run([str(self.exe),p,'task'],check=True)
   self.assertEqual(pathlib.Path(p,'my_game.pkg').read_text(),'MY GAME DATA')
   self.assertFalse(pathlib.Path(p,'journal.txt').exists())
 def test_rejects_unsafe_journal_data(self):
  with tempfile.TemporaryDirectory() as p:
   subprocess.run([str(self.exe),p,'invalid'],check=True)
   self.assertFalse(pathlib.Path(p,'journal.txt').exists())
 def test_rejects_package_changed_since_ui_scan(self):
  with tempfile.TemporaryDirectory() as p:
   subprocess.run([str(self.exe),p,'modified'],check=True)
 def test_previous_session_task_starts_blocked(self):
  code=(ROOT/'src/main.cpp').read_text()
  self.assertIn('read_pending_task(kPendingFile,pending)',code)
  self.assertIn('result.step="PREVIOUS_TASK_NOT_VERIFIED"',code)
  self.assertIn('if(ack && started)',code)
  self.assertIn('else if(journal_exists)',code)
  self.assertIn('acknowledge_pending_task(kPendingFile)',code)
  self.assertIn('if(!chepinstaller::unchanged_package(files[selected]))',code)
 def test_unchanged_titleid_and_separate_app(self):
  assert 'CHEP00002' in (ROOT/'Makefile').read_text()
  self.assertIn('0.33',(ROOT/'Makefile').read_text())
if __name__=='__main__':unittest.main()
