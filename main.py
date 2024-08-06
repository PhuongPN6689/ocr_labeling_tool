import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.gui import OCRLabelingTool
from src.handle import set_external_data


if __name__ == "__main__":
    app = OCRLabelingTool()
    set_external_data(app)
    app.mainloop()
