import pathlib
import subprocess
import tempfile
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
HARNESS=r'''
#include "pkg_scan.hpp"
#include <iostream>
#include <vector>
int main(int argc,char** argv){
 if(argc!=2 && argc!=3)return 3;
 std::vector<chepinstaller::PackageFile> out;std::string err;
 bool ok=argc==2 ? chepinstaller::scan_packages(argv[1],out,err) :
   chepinstaller::scan_package_locations({argv[1],argv[2]},out,err);
 std::cout<<"ok="<<ok<<" count="<<out.size()<<" err="<<err<<"\n";
 for(auto& f:out)std::cout<<f.filename<<"|"<<f.size<<"\n";
 return 0;
}
'''
class PackageScannerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory()
  cls.bin=pathlib.Path(cls.tmp.name)/'scanner'
  source=pathlib.Path(cls.tmp.name)/'test.cpp'
  source.write_text(HARNESS)
  subprocess.run(['g++','-std=c++11','-Wall','-Wextra','-Werror',
    '-I'+str(ROOT/'src'),str(source),str(ROOT/'src/pkg_scan.cpp'),'-o',str(cls.bin)],check=True)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def run_scan(self,directory):
  return subprocess.check_output([str(self.bin),str(directory)],text=True)
 def test_only_valid_finished_packages_sorted(self):
  with tempfile.TemporaryDirectory() as directory:
   root=pathlib.Path(directory)
   data=b'\x7fCNT'+b'\0'*8192
   (root/'Beta.pkg').write_bytes(data)
   (root/'Alpha.PKG').write_bytes(data)
   (root/'ignored.pkg.downloading').write_bytes(data)
   (root/'corrupt.pkg').write_bytes(b'\0'*8196)
   (root/'short.pkg').write_bytes(b'\x7fCNT')
   (root/'bad..name.pkg').write_bytes(data)
   (root/'alias.pkg').symlink_to(root/'Beta.pkg')
   result=self.run_scan(root)
   self.assertIn('ok=1 count=2',result)
   self.assertTrue(result.index('Alpha.PKG')<result.index('Beta.pkg'))
   self.assertNotIn('alias.pkg',result)
 def test_empty_directory(self):
  with tempfile.TemporaryDirectory() as directory:
   self.assertIn('count=0',self.run_scan(directory))
 def test_scan_both_primary_and_store_fallback(self):
  with tempfile.TemporaryDirectory() as directory:
   root=pathlib.Path(directory)
   primary=root/'pkg';fallback=root/'downloads'
   primary.mkdir();fallback.mkdir()
   good=b'\x7fCNT'+b'\0'*8192
   (primary/'primary.pkg').write_bytes(good)
   (fallback/'store.pkg').write_bytes(good)
   (fallback/'unfinished.pkg.downloading').write_bytes(good)
   output=subprocess.check_output([str(self.bin),str(primary),str(fallback)],text=True)
   self.assertIn('ok=1 count=2',output)
   self.assertIn('primary.pkg',output)
   self.assertIn('store.pkg',output)
   self.assertNotIn('unfinished.pkg.downloading',output)
  
 def test_optional_store_directory_missing(self):
  with tempfile.TemporaryDirectory() as directory:
   root=pathlib.Path(directory)
   primary=root/'pkg';primary.mkdir()
   (primary/'present.pkg').write_bytes(b'\x7fCNT'+b'\0'*8192)
   output=subprocess.check_output([str(self.bin),str(primary),str(root/'not-created')],text=True)
   self.assertIn('ok=1 count=1',output)
   self.assertNotIn('errno=2',output)

 def test_missing_directory(self):
  with tempfile.TemporaryDirectory() as directory:
   self.assertIn('ok=0',self.run_scan(pathlib.Path(directory)/'not_found'))
if __name__=='__main__':unittest.main()
