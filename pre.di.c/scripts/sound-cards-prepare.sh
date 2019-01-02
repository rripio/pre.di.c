#!/bin/bash

# Useful script for Desktop and Pulseaudio systems

# Release cards from Pulseaudio to be used in pre.di.c:
# DX
pactl set-card-profile alsa_card.pci-0000_02_04.0               off
# miniStreamer
pactl set-card-profile alsa_card.usb-miniDSP_miniStreamer-01    off
# Device
pactl set-card-profile alsa_card.usb-0d8c_USB_Sound_Device-00   off

# And restore our asound settigs for the cards used in pre.di.c:
alsactl -f ~/pre.di.c/config/asound.DX              restore DX
alsactl -f ~/pre.di.c/config/asound.Device          restore Device
alsactl -f ~/pre.di.c/config/asound.miniStreamer    restore miniStreamer
