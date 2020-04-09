#!/usr/bin/python3
import time
import tkinter as tk
import threading
import jack

# Global variables
clock = 0
status = "STOP"
playHead = 0
playCursor = None
pattern = {}
pattern_grid = {}
trackHeight=20
highlight = (0,0)

def drawPlayhead():
    gridCanvas.coords(playCursor, playHead*40, 12*trackHeight, playHead*40 + 40, 12*trackHeight + 10)
    gridCanvas.update()

def onCanvasClick(event):
    global highlight
    closest = event.widget.find_closest(event.x, event.y)
    for row,col in pattern_grid:
        if pattern_grid[(row,col)] == closest[0]:
            if((row,col) in pattern):
                del pattern[(row,col)]
                drawCell(highlight[0], highlight[1])
                drawCell(row, col, True)
                highlight = (row, col)
            else:
                pattern[(row,col)] = 100 #TODO Use current input value
                drawCell(highlight[0], highlight[1])
                drawCell(row, col, True)
                highlight = (row, col)

def drawCell(row, col, selected = False):
    global pattern_grid
    value = 255 - pattern[row,col]*2 if (row,col) in pattern else 255
    fill = "#%02x%02x%02x" % (value,value,value)
    if selected:
        on = '#883399'
    elif value == 0:
        on = 'black'
    else:
        on = '#dddddd'
    if (row,col) in pattern_grid:
        gridCanvas.itemconfig(pattern_grid[(row,col)], fill=fill, outline=on)
    else:
        pattern_grid[row,col] = gridCanvas.create_rectangle(col*40,row*trackHeight,col*40+39,row*trackHeight+19, fill=fill, outline=on, tags=(row,col))
        gridCanvas.tag_bind(pattern_grid[row,col], '<Button-1>', onCanvasClick)


def drawGrid(rows, cols):
    for row in range(rows):
        for col in range(cols):
            drawCell(col, row)

def noteOn(note, velocity):
    print("Note on:", note, velocity)

def onJackProcess(frames):
    global clock, status, playHead
    for offset, data in midiInput.incoming_midi_events():
        if data[0] == b'\xf8':
            # MIDI Clock
            if status == "PLAY":
                clock = clock + 1
                if clock >= 24:
                    # Time to process a time slot
                    clock = 0
                    playHead = playHead + 1
                    if playHead > 15:
                        playHead = 0
                    for row,col in pattern:
                        if col == playHead:
                            noteOn(row, pattern[row,col])
                        #TODO Send note off
                    drawPlayhead()
        elif data[0] == b'\xfa':
            # MIDI Start
            print("MIDI START")
            playHead = 0
            clock = 0
            status = "PLAY"
            drawPlayhead()
            gridCanvas.itemconfig(playCursor, state = 'normal')
        elif data[0] == b'\xfb':
            # Midi Continue
            print("MIDI CONTINUE")
            status = "PLAY"
            gridCanvas.itemconfig(playCursor, state = 'normal')
        elif data[0] == b'\xfc':
            # MIDI Stop
            print("MIDI STOP")
            status = "STOP"
            gridCanvas.itemconfig(playCursor, state = 'hidden')

def drawKey(note, offset):
    octave = note // 12
    relNote = note % 12
    if relNote in (0,2,4,5,7,9,11):
        print("White note")
    else:
        print("Black note")

def drawKeys(baseNote):
    pianoRoll.create_rectangle(0,0,100,trackHeight*1.5, fill="white")
    pianoRoll.create_rectangle(0,trackHeight*1.5,100,trackHeight*3.5, fill="white")
    pianoRoll.create_rectangle(0,trackHeight*3.5,100,trackHeight*5.5, fill="white")
    pianoRoll.create_rectangle(0,trackHeight*5.5,100,trackHeight*7.5, fill="white")
    pianoRoll.create_rectangle(0,trackHeight*6.5,100,trackHeight*8.5, fill="white")
    pianoRoll.create_rectangle(0,trackHeight*8.5,100,trackHeight*10.5, fill="white")
    pianoRoll.create_rectangle(0,trackHeight*10.5,100,trackHeight*12, fill="white")
    pianoRoll.create_rectangle(0,trackHeight,60,trackHeight*2, fill="black")
    pianoRoll.create_rectangle(0,trackHeight*3,60,trackHeight*4, fill="black")
    pianoRoll.create_rectangle(0,trackHeight*5,60,trackHeight*6, fill="black")
    pianoRoll.create_rectangle(0,trackHeight*8,60,trackHeight*9, fill="black")
    pianoRoll.create_rectangle(0,trackHeight*10,60,trackHeight*11, fill="black")

def updateHighlight(row, col):
    global highlight
    drawCell(highlight[0], highlight[1])
    print("Highlight was %d,%d" % (highlight[0], highlight[1]))
    highlight = (row, col)
    print(" and now is %d,%d" % (row, col))
    drawCell(highlight[0], highlight[1], True)
    gridCanvas.update()

def onKeyPress(event):
    if event.keycode == 98:
        #UP
        if highlight[0]:
            updateHighlight(highlight[0] - 1, highlight[1])
    elif event.keycode == 104:
        #DOWN
        if highlight[0] < 11:
            updateHighlight(highlight[0] + 1, highlight[1])
    elif event.keycode == 100:
        #LEFT
        if highlight[1]:
            updateHighlight(highlight[0], highlight[1] - 1)
    elif event.keycode == 102:
        #RIGHT
        if highlight[1] < 15:
            updateHighlight(highlight[0], highlight[1] + 1)
    

# Main application
if __name__ == "__main__":
    # Create GUI
    window = tk.Tk()
    pianoRoll = tk.Canvas(window, width=100, height=400, bg="white")
    drawKeys(60)
    pianoRoll.grid(row=0, column=0)
    gridCanvas = tk.Canvas(window, width=800, height=400, bg="#eeeeee")
    gridCanvas.grid(row=0, column=1)
    playCursor = gridCanvas.create_rectangle(0,12*trackHeight,40,12*trackHeight+10, fill="green", state="hidden")

    # For test populate pattern with some stuff
    for row in range(12):
        for col in range(16):
            if col == row:
                pattern[row,col] = row * 8

    drawGrid(16,12)
    window.bind("<Key>", onKeyPress)

    # Set up JACK interface
    jackClient = jack.Client("zynthstep")
    midiInput = jackClient.midi_inports.register("input")
    jackClient.set_process_callback(onJackProcess)
    jackClient.activate()
    #TODO: Remove auto test connection 
    jackClient.connect("a2j:MidiSport 2x2 [20] (capture): MidiSport 2x2 MIDI 1", "zynthstep:input")
    # Here we go....
    window.mainloop()
