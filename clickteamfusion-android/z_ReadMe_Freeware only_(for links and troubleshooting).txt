All software on this host are FREEWARE that can be downloaded from the creators websites.
Unfortunately, websites change over time and this can make finding the right files, overly difficult.
The only purpose of this website, is to prevent having to figure out which files to download.

Downloaded from:
https://drive.google.com/open?id=0ByViQxi6uPIaN1ZndzlZWDEydUE


-----------------------------------

There is a chance I downloaded the SDK from here, since it is in my browsing history:
http://filehippo.com/download_android_sdk/

With Avast Antivirus, I had to temporarily disable it, to install some things. It seems to cause files to be locked and unable to download or update for both Clickteam Fusion stuff and even the Steam Client. You may also have issues with any of these installs where disabling it during download/install is required. I don’t know why Avast has this issue, Malwarebytes Premium doesn’t find any issues.


------------------------------------------------------------------------------------------------------------

https://community.clickteam.com/threads/79925-Setting-up-the-Android-SDK-for-the-Android-Export-Module

*1* http://www.oracle.com/technetwork/java/javase/downloads/index.html
*2* http://developer.android.com/sdk/index.html


*1*
You need to download and install 2 external packages : 
You need to install the Java Development Kit, version 6. Note: JDK 7 is not fully compatible with the Android SDK, especially for the signature of the applications, install JDK 6 instead. The first time you build an Android application, Multimedia Fusion 2 Developer will ask you for the pathname of the JDK directory, select it in the folder selector. For example C:\Program Files (x86)\Java\jdk1.6.0_33. You can later change it in the preferences if necessary. Note for 64-bit machines : install at least the 32-bit version of the JDK, not only the 64-bit version. The 64-bit version may cause a conflict with the SWF exporter.

*2*
You need to install the Android SDK. Do not install the ADT Bundle. Click "Use an existing IDE" and then download the "SDK Tools for Windows" (EXE installer). And then in the Android SDK Manager install at least the Android 4.0 platform package (API #14). When you build your first Android application Multimedia Fusion 2 or Multimedia Fusion 2 Developer will ask you for the pathname of the Android SDK directory. You can change it at any time in the preferences of Multimedia Fusion 2 or Multimedia Fusion 2 Developer.

And later when you want to release applications: 
You will need a certificate to sign your applications before being able to release them.
If you want to publish applications on the Android Market, you will need to register a developer account on https://market.android.com/publish/signup ($25).

Where to find documentation about Android development ?
Although the export module makes it simple to develop an Android application, you will still need to read Google's documentation, especially and the sections that explain how to publish your application, test it, etc. The main page for Android development can be found at : http://developer.android.com/index.html


Minimum requirements for Android applications created with Multimedia Fusion 2 or Multimedia Fusion 2 Developer
Android applications created with the export module require Android 2.2 or above, and Android devices with a GPU (graphic processor). Applications created will run on Android devices without GPU but they will be very slow.
