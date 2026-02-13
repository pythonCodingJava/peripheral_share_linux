[![Build Status](https://travis-ci.com/quangthanh010290/keyboard_mouse_emulate_on_raspberry.svg?branch=master)](https://travis-ci.com/quangthanh010290/keyboard_mouse_emulate_on_raspberry)

# Make things work first

## Step 1: Setup

```
 sudo ./setup.sh
```


## Step 2.1: Add your host mac
Run the `share.py` file as sudo.

# Credits 
https://github.com/thanhlev/keyboard_mouse_emulate_on_raspberry
This repository provided the basic bluetooth hid template, several changes were made in the sdp records and also adding dummy control and interrupt acknowledgers to help stabilize the connections, thus this is kept as a separate repository.