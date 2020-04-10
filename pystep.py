#!/usr/bin/python3
import time
import tkinter as tk
import threading
import jack

# Global variables
clock = 0 # Count of MIDI clock pulses since last step [0..24]
status = "STOP" # Play status [STOP | PLAY]
playHead = 0 # Play head position in steps [0..gridColumns]
playCursor = None # Rectangle representing play head position
pattern = {} # Dictionary of notes in pattern TODO: This is currently tied to grid
pattern_grid = {} # Dictionary of rectangle widget IDs indexed by (row,column)
trackHeight=20 # Grid row height in pixels
gridRows = 16 # Quantity of rows in grid
gridColumns = 16 # Quantity of columns in grid
keyOrigin = 60 # MIDI note number of top row in grid
highlight = (0,0) # Location of highlighted cell (row, column)
# keys: Array of keys in octave, indexed by offset from C with array of: isWhite, start y-offset, end y-offset
keys = ((True, 0, 1.5),(False, 0, 1),(True, -0.5, 1.5),(False, 0, 1),(True, -0.5, 1.5),(False, 0, 1),(True, -0.5, 1),(True, 0, 1.5),(False, 0, 1),(True, -0.5, 1.5),(False, 0, 1),(True, -0.5, 1))

# Function to draw the play head cursor
def drawPlayhead():
    gridCanvas.coords(playCursor, playHead*40, gridRows*trackHeight, playHead*40 + 40, gridRows*trackHeight + 10)
    gridCanvas.update()

# Function to handle mouse click / touch
#   event: Mouse event
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

# Function to draw a grid cell
#   row: Row index
#   col: Column index
#   selected: True if cell is selected (default: False)
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

# Function to draw grid
#   rows: Quantity of rows
#   columns: Quantity of columns
def drawGrid(rows, cols):
    for row in range(rows):
        for col in range(cols):
            drawCell(col, row)

# Function to send MIDI note on
#   note: MIDI note number
#   velocity: MIDI velocity
#   NOTE: Which channel?
def noteOn(note, velocity):
    print("Note on:", note, velocity)
    #TODO: Implement noteOn

# Function to handle JACK process events
#   frames: Quantity of frames since last process event
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

# Function to draw piano-roll
#   baseNote: MIDI note number of first (top) note to display
def drawPianoroll(baseNote):
    for offset in range(0, gridRows):
        print("Offset:", offset)
        key = keys[(offset + baseNote) % 12]
        print("Key:",key)
        if key[0]:
            # White key
            x1 = 0
            y1 = trackHeight * (offset + key[1])
            x2 = 100
            y2 = trackHeight * (offset + key[2])
            print("Drawing white key at offset %d: (%d,%d) (%d,%d)" % (offset,x1,y1,x2,y2))
            pianoRoll.create_rectangle(x1, y1, x2, y2, fill="white")
    for offset in range(0, gridRows):
        key = keys[(offset + baseNote) % 12]
        if not key[0]:
            # Black key
            x1 = 0
            y1 = trackHeight * (offset + key[1])
            x2 = 60
            y2 = trackHeight * (offset + key[2])
            pianoRoll.create_rectangle(x1, y1, x2, y2, fill="black")

# Function to update highlight of currently selected cell
#   row: Row of selected cell
#   col: Column index of selected cell
# NOTE: Removes previous highlight
def updateHighlight(row, col):
    global highlight
    drawCell(highlight[0], highlight[1])
    print("Highlight was %d,%d" % (highlight[0], highlight[1]))
    highlight = (row, col)
    print(" and now is %d,%d" % (row, col))
    drawCell(highlight[0], highlight[1], True)
    gridCanvas.update()

# Function to handle keyboard key press event
#   event: Key event
def onKeyPress(event):
    if event.keycode == 98:
        #UP
        if highlight[0]:
            updateHighlight(highlight[0] - 1, highlight[1])
    elif event.keycode == 104:
        #DOWN
        if highlight[0] < gridRows - 1:
            updateHighlight(highlight[0] + 1, highlight[1])
    elif event.keycode == 100:
        #LEFT
        if highlight[1]:
            updateHighlight(highlight[0], highlight[1] - 1)
    elif event.keycode == 102:
        #RIGHT
        if highlight[1] < gridColumns - 1:
            updateHighlight(highlight[0], highlight[1] + 1)

# Main application
if __name__ == "__main__":
    # Create GUI
    window = tk.Tk()
    pianoRoll = tk.Canvas(window, width=100, height=400, bg="white")
    drawPianoroll(keyOrigin)
    pianoRoll.grid(row=0, column=0)
    gridCanvas = tk.Canvas(window, width=800, height=400, bg="#eeeeee")
    gridCanvas.grid(row=0, column=1)
    playCursor = gridCanvas.create_rectangle(0,gridRows*trackHeight,40,gridRows*trackHeight+10, fill="green", state="hidden")

    # For test populate pattern with some stuff
    for row in range(gridRows):
        for col in range(gridColumns):
            if col == row:
                pattern[row,col] = row * 8

    drawGrid(gridColumns,gridRows)
    window.bind("<Key>", onKeyPress)

    # Set up JACK interface
    jackClient = jack.Client("zynthstep")
    midiInput = jackClient.midi_inports.register("input")
    midiOutput = jackClient.midi_outports.register("output")
    jackClient.set_process_callback(onJackProcess)
    jackClient.activate()
    #TODO: Remove auto test connection 
    jackClient.connect("a2j:MidiSport 2x2 [20] (capture): MidiSport 2x2 MIDI 1", "zynthstep:input")
    # Here we go....
    window.mainloop()
