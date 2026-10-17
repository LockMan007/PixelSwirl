GFWL Fatality 0.1.0

I Just want to fight now Quick Start!

1. Extract this ZIP.
2. Windows: double-click install-windows.cmd.
3. Steam Deck: double-click install-steamdeck.desktop in Desktop Mode.

The installers are convenience wrappers. All they really do is copy xlive.dll next to the game binary:
  Mortal Kombat Arcade Kollection/BINARIES/WIN32/xlive.dll

Steam Deck setup should also be useful on most Linux distributions running the Windows version of MKAK through Proton or Wine. If Wine/Proton does not pick up the local DLL automatically, set a DLL override for xlive to native,builtin.

Target:
  Mortal Kombat Arcade Kollection

Windows:
  Right-click install-windows.cmd and choose Run as administrator if the game is under Program Files.

Steam Deck / Linux:
  Copy this folder to the Deck.
  In Desktop Mode, try opening install-steamdeck.desktop.
  If SteamOS asks, mark it trusted/executable first.
  You can also run:
    bash ./install-steamdeck.sh

The installer copies xlive.dll into:
  Mortal Kombat Arcade Kollection/BINARIES/WIN32/xlive.dll

This is an unofficial local-profile compatibility shim. It does not provide online GFWL services.
