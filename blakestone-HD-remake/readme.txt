THIS IS INCOMPLETE.
A WORK IN PROGRESS.
I still need to do 270-305 (35 frames)

check out the preview: https://github.com/LockMan007/PixelSwirl/blob/main/blakestone-HD-remake/preview-low-res.png

UPDATE 1/3/2026:
I just found out that i have to stretch all my images by 20% horizontally, because the source port stretches them.
If i understand correctly, the 1024x1024 must remain the same size,
but the sprite in the image, needs to be resized to be 20% wider.
1024 x 1024
becomes
1229 x 1024
then copy/paste back into a 1024x1024 image.

-------------------------------------------------------------------------------------------
Quote:
The port stretches the geometry (world, objects) vertically by 20%. That means if you created a wall or sprite texture, for example, with physical dimensions 1024x1024 it will be rendered as 1024x1228, i.e. stretched.
Flooring and ceiling textures has always 1:1 aspect ratio.
TLDR
Design wall, sprite, HUD element or screen images in 1:1.2 aspect ratio (i.e. 1280x1536), but export for the game in 1:1 aspect ratio (i.e. 1024x1024).
Design flooring or ceiling image in 1:1 aspect ratio (i.e. 1280x1280), and export for the game in 1:1 aspect ratio (i.e. 1024x1024) too.
End Quote.
-------------------------------------------------------------------------------------------

My old method:
getting rid of fuchsia color background from upscaled images was a MASSIVE pain.
The fuchsia color acts like a light and shines onto the character, which makes it very difficult to remove without destroying the image.

I did color replace, 
and then Due/Saturation to change Fuchsia to white, but now the white is left behind.
then added a black stroke/outline.

info:
I've had to manually edit every picture many times, so don't think this is just "oh he just gave the image to AI and said 'do it'" because in spite of how good AI is, and all my experience with AI, it's still not perfect, even with Nano Banana.

UPDATED method: I am now using a white background.
There is no need to use Fuchsia in 2025, it's just going to cause problems unless you are doing pixel by pixel editing and no transparency.

I'm using Z-Image on my local GPU and photoshop.
It takes a lot of attempts to get a face that matches and a minimal amount of image defects.
Often the informant clipboard is wrong and i have to manually fix it, as long as it gets the size close enough, sometimes it makes it square.

i've generated about 250 images, and done countless photo edits, to just get 13 frames done.
It takes a lot of work.

Fan made Source Port required:
https://github.com/bibendovsky/bstone/releases/

Fan made AI Upscale:
https://www.nexusmods.com/blakestonealiensofgold/mods/1?tab=description

Youtube video made by the person who made the AI upscale images:
https://www.youtube.com/watch?v=4_3rdT0c8i0


My images here are for addictions to the Fan made AI Upscale, as an alternative for this one character in the game.
The person who made teh AI upscale is currently working on doing it themselves with their own art style, to fix the issues.


---------------------------------------------------------------------------------------
the process, now that i got it down is:
- take original sprite sheet.
- copy/paste out 1 frame
- resize with "nearest neighbor" to keep pixels, from 64x64 to 1024x1024
- change background to WHITE.
- if needed, edit some in photoshop first, it helps a ton.
- bring into ComfyUI, Denoise 50-80% (typically 65 is working most of the time best) Z-IMAGE
prompting to describe, waiting for a good output.
- bring it back into photoshop, make fixes to problems
- delete the background.
- add a black stroke to the middle edge of the image,
- go and manually erase all the tiny specs that shouldn't be there on the edges
- save
