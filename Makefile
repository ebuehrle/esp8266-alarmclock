PORT=/dev/tty.wchusbserial1a160

.PHONY: transfer
transfer: base.transfered main.transfered periph.transfered views.transfered tft.transfered st7735.transfered font.transfered wifimgr.transfered

.PHONY: clean
clean:
	rm -f *.mpy
	rm -f *.transfered

.SUFFIXES: .py .mpy .transfered

.mpy.transfered:
	# make sure nothing is using the serial connection
	ampy -p $(PORT) -b 115200 -d 0.5 put $<
	touch $@

.py.mpy: 
	python3 -m mpy_cross $<

%.py: */%.py
	cp $< .
