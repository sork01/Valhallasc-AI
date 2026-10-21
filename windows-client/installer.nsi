; Installer for the Valhalla Rumble Windows client. Built on Linux with makensis (see build.sh):
; electron-builder's own NSIS target needs wine, a plain script does not.
Unicode true
!define APP "Valhalla Rumble"
!define REGKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\se.gunning.valhallasc"
!ifndef VERSION
  !define VERSION "1.0.0"
!endif
!ifndef SRC
  !error "pass -DSRC=<win-unpacked dir>"
!endif
!ifndef ICON
  !error "pass -DICON=<icon.ico>"
!endif
!ifndef OUT
  !define OUT "Valhalla-Rumble-Setup-${VERSION}.exe"
!endif

Name "${APP}"
OutFile "${OUT}"
InstallDir "$LOCALAPPDATA\Programs\${APP}"
InstallDirRegKey HKCU "Software\se.gunning.valhallasc" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
SetCompressorDictSize 32

!include "MUI2.nsh"
!define MUI_ICON "${ICON}"
!define MUI_UNICON "${ICON}"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\Valhalla Rumble.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Start Valhalla Rumble"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "${APP}"
VIAddVersionKey "FileDescription" "${APP} installer"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "LegalCopyright" "sork01"

Section "Install"
  ; a running copy would keep its files locked
  nsExec::Exec 'taskkill /F /IM "Valhalla Rumble.exe"'
  SetOutPath "$INSTDIR"
  File /r "${SRC}\*.*"
  File "/oname=icon.ico" "${ICON}"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateShortCut "$DESKTOP\${APP}.lnk" "$INSTDIR\Valhalla Rumble.exe" "" "$INSTDIR\icon.ico"
  CreateDirectory "$SMPROGRAMS\${APP}"
  CreateShortCut "$SMPROGRAMS\${APP}\${APP}.lnk" "$INSTDIR\Valhalla Rumble.exe" "" "$INSTDIR\icon.ico"
  CreateShortCut "$SMPROGRAMS\${APP}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\se.gunning.valhallasc" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${REGKEY}" "DisplayName" "${APP}"
  WriteRegStr HKCU "${REGKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${REGKEY}" "Publisher" "sork01"
  WriteRegStr HKCU "${REGKEY}" "DisplayIcon" "$INSTDIR\icon.ico"
  WriteRegStr HKCU "${REGKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${REGKEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKCU "${REGKEY}" "NoModify" 1
  WriteRegDWORD HKCU "${REGKEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  nsExec::Exec 'taskkill /F /IM "Valhalla Rumble.exe"'
  Delete "$DESKTOP\${APP}.lnk"
  RMDir /r "$SMPROGRAMS\${APP}"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKCU "${REGKEY}"
  DeleteRegKey HKCU "Software\se.gunning.valhallasc"
SectionEnd
