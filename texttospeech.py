import sys
import pyttsx3
import threading
import fitz         # PyMuPDF
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QComboBox, QSlider, QFileDialog, QTextEdit, QHBoxLayout, QGraphicsView, QGraphicsScene, QLineEdit
from PyQt5.QtGui import QPixmap, QImage

# Initialize the TTS engine for only the voice drop-box
engine = pyttsx3.init()

# Start engine as a class, so I can delete the object later, because the runandwait function gets blocked
class _TTS:
    engine = None
    rate = None
    def __init__(self):
        self.engine = pyttsx3.init()
    
    def start(self,text_):
        self.engine.say(text_)
        self.engine.runAndWait()

    def settings(self, rate, volume, selected_voice):
        self.engine.setProperty('volume', volume)
        self.engine.setProperty('voice', selected_voice)
        self.engine.setProperty('rate', rate)

class TTSApp(QWidget):
    def __init__(self):
        super().__init__()

        self.pdf_document = None  # Track the opened PDF document
        self.current_page = 0  # Track the current page being viewed
        self.total_pages = 0  # Track the total number of pages in the PDF
        self.stop_flag = False  # Flag to stop speech

        self.initUI()

    def initUI(self):
        # Window properties
        self.setWindowTitle("Book Reader with PDF Viewer")
        self.setGeometry(420, 200, 1000, 700)  # Increase window size for PDF viewer

        # Main Layout (horizontal to have controls on the left and PDF on the right)
        main_layout = QHBoxLayout()

        # Left layout for controls
        left_layout = QVBoxLayout()

        # Button to open file dialog
        self.open_button = QPushButton("Open PDF File", self)
        self.open_button.clicked.connect(self.open_file_dialog)
        left_layout.addWidget(self.open_button)

        # Text box to display PDF content (text)
        self.text_box = QTextEdit(self)
        self.text_box.setReadOnly(True)
        left_layout.addWidget(self.text_box)

        # Voice selection dropdown
        self.voice_combo = QComboBox(self)
        self.populate_voices()
        left_layout.addWidget(self.voice_combo)

        # Rate control slider
        self.rate_slider = QSlider(self)
        self.rate_slider.setOrientation(1)  # Horizontal slider
        self.rate_slider.setMinimum(50)
        self.rate_slider.setMaximum(300)
        self.rate_slider.setValue(150)
        self.rate_slider.setTickPosition(QSlider.TicksBelow)
        self.rate_slider.setTickInterval(10)
        left_layout.addWidget(QLabel("Speech Rate:"))
        left_layout.addWidget(self.rate_slider)

        # Volume control slider
        self.volume_slider = QSlider(self)
        self.volume_slider.setOrientation(1)  # Horizontal slider
        self.volume_slider.setMinimum(1)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(100)
        left_layout.addWidget(QLabel("Volume:"))
        left_layout.addWidget(self.volume_slider)

        # Button to trigger speech
        self.speak_button = QPushButton("Speak", self)
        self.speak_button.clicked.connect(self.start_speaking_thread)
        left_layout.addWidget(self.speak_button)

        # Button to stop speech
        self.stop_button = QPushButton("Stop Speaking", self)
        self.stop_button.clicked.connect(self.stop_speaking)
        left_layout.addWidget(self.stop_button)

        # Right layout for PDF viewer and page navigation
        right_layout = QVBoxLayout()

        # PDF viewer
        self.pdf_viewer = QGraphicsView(self)
        self.scene = QGraphicsScene(self)
        self.pdf_viewer.setScene(self.scene)
        right_layout.addWidget(self.pdf_viewer)  # Add the viewer to the right layout

        # Horizontal layout for navigation buttons (under PDF viewer)
        navigation_layout = QHBoxLayout()
        self.prev_page_button = QPushButton("Previous Page", self)
        self.prev_page_button.clicked.connect(self.show_previous_page)
        self.next_page_button = QPushButton("Next Page", self)
        self.next_page_button.clicked.connect(self.show_next_page)

        # Add buttons to the navigation layout
        navigation_layout.addWidget(self.prev_page_button)

        # Create a QLabel to show the current page number
        self.page_label = QLabel("Page 1 of 1", self)  # Default text
        navigation_layout.addWidget(self.page_label)

        # Page number input field
        self.page_input = QLineEdit(self)
        self.page_input.setPlaceholderText("Enter page number")
        navigation_layout.addWidget(self.page_input)

        # Button to go to the specified page
        self.go_page_button = QPushButton("Go", self)
        self.go_page_button.clicked.connect(self.go_to_page)
        navigation_layout.addWidget(self.go_page_button)

        navigation_layout.addWidget(self.next_page_button)

        # Add navigation layout (buttons) under the PDF viewer
        right_layout.addLayout(navigation_layout)

        # Add layouts to the main horizontal layout
        main_layout.addLayout(left_layout)  # Left controls and text display
        main_layout.addLayout(right_layout)  # Right PDF viewer and navigation

        # Set the layout to the window
        self.setLayout(main_layout)

        # Disable navigation buttons initially
        self.prev_page_button.setEnabled(False)
        self.next_page_button.setEnabled(False)

    def populate_voices(self):
        voices = engine.getProperty('voices')
        for voice in voices:
           self.voice_combo.addItem(voice.name, voice.id)

    def start_speaking_thread(self):
        # Reset the stop flag
        self.stop_flag = False

        # Start speaking in a separate thread
        self.speaking_thread = threading.Thread(target=self.speak)
        self.speaking_thread.start()

    def speak(self):
        # Initialize the engine
        tts = _TTS()
        
        # Disable the speak button while speaking
        self.speak_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        # Get the selected voice
        selected_voice = self.voice_combo.currentData()

        # Set the rate from the slider
        rate = self.rate_slider.value()

        # Set the volume from the slider
        volume = self.volume_slider.value() / 100  # Normalize to 0-1

        tts.settings(rate, volume, selected_voice)

        # Get the text from the current page (from the text box)
        current_page_text = self.text_box.toPlainText()

        # Chunk the text into smaller parts
        chunk_size = 50  # Number of characters per chunk
        for i in range(0, len(current_page_text), chunk_size):
            if self.stop_flag:  # Check if stop has been requested
                del(tts)
                break  # Exit the loop if stop is triggered
            # Speak each chunk separately
            chunk = current_page_text[i:i + chunk_size]
            tts.start(chunk)

        # Enable the speak button again
        self.speak_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def stop_speaking(self):
        # Set the stop flag to True to halt ongoing speech
        self.stop_flag = True

    def open_file_dialog(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open PDF File", "", "PDF Files (*.pdf)", options=options)

        if file_path:
            self.load_pdf(file_path)  # Load and display the PDF

    def load_pdf(self, file_path):
        # Open the PDF using PyMuPDF (fitz)
        self.pdf_document = fitz.open(file_path)
        self.total_pages = len(self.pdf_document)  # Set the total number of pages

        self.current_page = 0  # Start from the first page
        self.display_pdf(self.current_page)  # Display the first page

        # Update the page label
        self.update_page_label()

        # Enable the navigation buttons after loading the PDF
        self.update_navigation_buttons()

    def display_pdf(self, page_number):
        if self.pdf_document is None:
            return

        # Clear the previous scene (if any)
        self.scene.clear()

        # Load the specified page
        page = self.pdf_document.load_page(page_number)
        pix = page.get_pixmap()

        # Convert the pixmap to QImage
        qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)

        # Convert QImage to QPixmap and display it in the scene
        pixmap = QPixmap.fromImage(qimage)
        self.scene.addPixmap(pixmap)
        self.pdf_viewer.fitInView(self.scene.itemsBoundingRect(), 1)  # Fit the page in the viewer

        # Update the page label after displaying the page
        self.update_page_label()

        # Extract and display the text for the current page
        self.extract_text_for_page(page_number)

    def extract_text_for_page(self, page_number):
        page = self.pdf_document.load_page(page_number)
        page_text = page.get_text("text")
        self.text_box.setText(page_text)

    def show_next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.display_pdf(self.current_page)
            self.update_navigation_buttons()

    def show_previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.display_pdf(self.current_page)
            self.update_navigation_buttons()

    def go_to_page(self):
        try:
            page_number = int(self.page_input.text()) - 1  # Convert to zero-based index
            if 0 <= page_number < self.total_pages:
                self.current_page = page_number
                self.display_pdf(self.current_page)
                self.update_navigation_buttons()
            else:
                self.page_input.clear()  # Clear input if the number is out of range
        except ValueError:
            self.page_input.clear()  # Clear input if it's not a valid number

    def update_navigation_buttons(self):
        # Disable 'Previous' button if on the first page
        self.prev_page_button.setEnabled(self.current_page > 0)
        
        # Disable 'Next' button if on the last page
        self.next_page_button.setEnabled(self.current_page < self.total_pages - 1)

    def update_page_label(self):
        # Update the label with current page information
        self.page_label.setText(f"Page {self.current_page + 1} of {self.total_pages}")

# Main loop
if __name__ == '__main__':
    app = QApplication(sys.argv)
    tts_app = TTSApp()
    tts_app.show()
    sys.exit(app.exec_())
