CHEPGAME.NET - SUPER MANH | STORE + INSTALLER

Store v0.4.4: .github/workflows/build-ps4.yml, Title ID CHEP00001, download-only.
Installer v0.3.2: .github/workflows/build-chepgame-installer.yml, Title ID CHEP00002, install from /data/pkg/.

Both app sources can be uploaded to the root of the same GitHub repository.
Choose the appropriate GitHub Actions workflow for each app.

Installer v0.3.2 automatically fetches the upstream verified JBC at build time; this ZIP DOES NOT contain JBC binary.
Default installer build is not diagnostic: diagnostic_without_jbc=false.
Diagnostic builds have no install capability.

See README_HUONG_DAN.md (Store) and README_INSTALLER_v0.3.2.md (Installer).
