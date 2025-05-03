from escpos.printer import Usb

p = Usb(0x0485, 0x5741)
p.text("Hello from Pi over USB!\n")
p.cut()
