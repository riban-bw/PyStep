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
pattern = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]] # Array of notes in pattern, indexed by step: each step is array of events, each event is array of (note,velocity)
pattern_grid = {} # Dictionary of rectangle widget IDs indexed by (row,column)
trackHeight=20 # Grid row height in pixels
gridRows = 16 # Quantity of rows in grid
gridColumns = 16 # Quantity of columns in grid
keyOrigin = 60 # MIDI note number of top row in grid
selectedCell = (0,0) # Location of selectedCelled cell (row, column)
# keys: Array of keys in octave, indexed by offset from C with array of: isWhite, start y-offset, end y-offset
keys = ((True, 0, 1.5),(False, 0, 1),(True, -0.5, 1.5),(False, 0, 1),(True, -0.5, 1.5),(False, 0, 1),(True, -0.5, 1),(True, 0, 1.5),(False, 0, 1),(True, -0.5, 1.5),(False, 0, 1),(True, -0.5, 1))
inputVel = 100

# Function to draw the play head cursor
def drawPlayhead():
    gridCanvas.coords(playCursor, playHead*40, gridRows*trackHeight, playHead*40 + 40, gridRows*trackHeight + 10)

# Function to handle mouse click / touch
#   event: Mouse event
def onCanvasClick(event):
    closest = event.widget.find_closest(event.x, event.y)
    for row,col in pattern_grid:
        if pattern_grid[(col,row)] == closest[0]:
            # TODO: Should be better way to find cell's coords!!!
            toggleEvent(col, [row + keyOrigin, inputVel])

# Function to toggle note event
#   step: step (column) index
#   note: note list [note, velocity]
def toggleEvent(step, note):
    global selectedCell
    if step > gridRows or step > gridColumns:
        return
    found = False
    for event in pattern[step]:
        if event[0] == note[0]:
            pattern[step].remove(event)
            found = True
            break
    if not found:
        pattern[step].append(note)
    if note[0] >= keyOrigin and note[0] < keyOrigin + gridRows:
        selectCell(step, note[0] - keyOrigin)

# Function to draw a grid cell
#   col: Column index
#   row: Row index
def drawCell(col, row):
    global pattern_grid
    value = 255 # White
    for note in pattern[col]:
        if note[0] == row + keyOrigin:
            # Found cell with note
            value = 255 - note[1]*2
    fill = "#%02x%02x%02x" % (value,value,value)
    if selectedCell == (col, row):
        on = '#00ff00'
    elif value == 0:
        on = 'black'
    else:
        on = '#dddddd'
    if (col,row) in pattern_grid:
        gridCanvas.itemconfig(pattern_grid[(col,row)], fill=fill, outline=on)
    else:
        pattern_grid[col,row] = gridCanvas.create_rectangle(col*40,row*trackHeight,col*40+39,row*trackHeight+19, fill=fill, outline=on, tags=(row,col))
        gridCanvas.tag_bind(pattern_grid[col,row], '<Button-1>', onCanvasClick)


# Function to draw grid
#   columns: Quantity of columns
#   rows: Quantity of rows
def drawGrid(cols, rows):
    for col in range(cols):
        for row in range(rows):
            drawCell(col, row)

# Function to send MIDI note on
#   note: Array (MIDI note number, MIDI velocity)
#   NOTE: Which channel?
def noteOn(note):
    print("Note on:", 0, (0x90, note[0], note[1]))
    midiOutput.write_midi_event(0, (0x90, note[0], note[1]))

# Function to send MIDI note off
#   note: Array (MIDI note number, MIDI velocity)
#   NOTE: Which channel?
def noteOff(note):
    print("Note off:", 0, (0x80, note[0], note[1]))
    midiOutput.write_midi_event(0, (0x80, note[0], note[1]))

# Function to handle JACK process events
#   frames: Quantity of frames since last process event
def onJackProcess(frames):
    global clock, status, playHead
    midiOutput.clear_buffer();
    for offset, data in midiInput.incoming_midi_events():
        if data[0] == b'\xf8':
            # MIDI Clock
            if status == "PLAY":
                clock = clock + 1
                if clock >= 24:
                    # Time to process a time slot
                    clock = 0
                    for note in pattern[playHead]:
                        noteOff(note)
                    playHead = playHead + 1
                    if playHead > 15:
                        playHead = 0
                    for note in pattern[playHead]:
                        noteOn(note)
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
        key = keys[(offset + baseNote) % 12]
        if key[0]:
            # White key
            x1 = 0
            y1 = trackHeight * (offset + key[1])
            x2 = 100
            y2 = trackHeight * (offset + key[2])
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

# Function to update selectedCell
#   col: Column index of selected cell
#   row: Row index of selected cell
# NOTE: Removes previous selectedCell
def selectCell(col, row):
    global selectedCell
    previousSelected = selectedCell
    selectedCell = (col, row)
    drawCell(previousSelected[0], previousSelected[1])
    drawCell(selectedCell[0], selectedCell[1])

# Function to handle keyboard key press event
#   event: Key event
def onKeyPress(event):
    if event.keycode == 98:
        #UP
        if selectedCell[1]:
            selectCell(selectedCell[0], selectedCell[1] - 1)
    elif event.keycode == 104:
        #DOWN
        if selectedCell[1] < gridRows - 1:
            selectCell(selectedCell[0], selectedCell[1] + 1)
    elif event.keycode == 100:
        #LEFT
        if selectedCell[0]:
            selectCell(selectedCell[0] - 1, selectedCell[1])
    elif event.keycode == 102:
        #RIGHT
        if selectedCell[0] < gridColumns - 1:
            selectCell(selectedCell[0] + 1, selectedCell[1])
    elif event.keycode == 36:
        #ENTER
        toggleEvent(selectedCell[0], [keyOrigin + selectedCell[1], inputVel])
    elif event.keycode == 65:
        #SPACE
        pass
    else:
        print("Keypress code:", event.keycode)

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
    for col in range(gridColumns):
        for row in range(gridRows):
            if col == row:
                pattern[col].append([row + 60, row * 8])
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
    jackClient.connect("zynthstep:output", "ZynMidiRouter:main_in")
    # Here we go....
    window.mainloop()
