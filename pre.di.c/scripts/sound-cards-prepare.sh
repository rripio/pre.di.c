#!/bin/bash

# Useful script for Desktop and Pulseaudio systems.
# If used, PLEASE place at FIRST position inside config/scripts

# CARDS BELOW ARE A USER CASE, PLEASE UPDATE WITH YOURS

# Release cards from Pulseaudio to be used by pre.di.c:
# DX
pactl set-card-profile alsa_card.pci-0000_02_04.0               off
# miniStreamer
pactl set-card-profile alsa_card.usb-miniDSP_miniStreamer-01    off
# Device
pactl set-card-profile alsa_card.usb-0d8c_USB_Sound_Device-00   off

# And restore our asound settigs for the cards used by pre.di.c
# (i) asound.XXX files can be stored after you have set properly adjustements on alsamixer
alsactl -f ~/pre.di.c/config/asound.DX              restore DX
alsactl -f ~/pre.di.c/config/asound.Device          restore Device
alsactl -f ~/pre.di.c/config/asound.miniStreamer    restore miniStreamer
