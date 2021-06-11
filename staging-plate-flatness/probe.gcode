; move head up
G0 Z23

; probing starting from front left
G0 X20 Y20

G0 Z5

G4 P20000

G0 Z23

;probing starting front left edge
G0 X120 Y20

G0 Z5

G4 P20000

G0 Z23

;probing starting front center
G0 X220 Y20

G0 Z5

G4 P20000

G0 Z23

;probing starting front right edge
G0 X320 Y20

G0 Z5

G4 P20000

G0 Z23

;probing starting front right
G0 X420 Y20

G0 Z5

G4 P20000

G0 Z23

;probing starting back right
G0 X420 Y50

G0 Z5

G4 P20000

G0 Z23

;probing starting back right edge
G0 X320 Y50

G0 Z5

G4 P20000

G0 Z23

;probing starting back center
G0 X220 Y50

G0 Z5

G4 P20000

G0 Z23

;probing starting back left edge
G0 X120 Y50

G0 Z5

G4 P20000

G0 Z23

;probing starting back left
G0 X20 Y50

G0 Z5

G4 P20000

G0 Z23

M400
M118 test