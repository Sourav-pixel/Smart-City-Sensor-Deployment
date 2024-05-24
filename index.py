import customtkinter as ctk
from tkinter import filedialog
from PIL import Image, ImageTk
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import threading
import cv2
from collections import deque


class SensorDeploymentApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Smart City Sensor Deployment")
        self.geometry("800x800")

        # Set the theme
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # Create the main layout
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Input fields
        self.area_width_input = ctk.CTkEntry(self.main_frame, placeholder_text="Area Width (meters)")
        self.area_width_input.pack(pady=10)

        self.area_height_input = ctk.CTkEntry(self.main_frame, placeholder_text="Area Height (meters)")
        self.area_height_input.pack(pady=10)

        self.grid_size_input = ctk.CTkEntry(self.main_frame, placeholder_text="Grid Size (meters)")
        self.grid_size_input.pack(pady=10)

        self.sensor_range_input = ctk.CTkEntry(self.main_frame, placeholder_text="Sensor Range (meters)")
        self.sensor_range_input.pack(pady=10)

        # Buttons for loading map and deploying sensors
        self.load_map_button = ctk.CTkButton(self.main_frame, text="Load Map", command=self.load_map)
        self.load_map_button.pack(pady=10)

        self.deploy_sensors_button = ctk.CTkButton(self.main_frame, text="Deploy Sensors", command=self.start_deployment)
        self.deploy_sensors_button.pack(pady=10)

        # Display area for the map image
        self.map_label = ctk.CTkLabel(self.main_frame, text="No map loaded")
        self.map_label.pack(pady=10)

        # Progress bar for indicating progress
        self.progress_bar = ctk.CTkProgressBar(self.main_frame, mode="determinate")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10, fill="x")

        self.map_image = None
        self.image_reference = None  # To maintain image reference

    def load_map(self):
        # Open a file dialog to select the map image
        file_path = filedialog.askopenfilename(
            title="Open Map Image",
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp;*.tiff")]
        )
        if file_path:
            self.map_image = Image.open(file_path)
            image_resized = self.map_image.resize((300, 300))  # Resize for display
            self.image_reference = ImageTk.PhotoImage(image_resized)  # Keep reference
            self.map_label.configure(image=self.image_reference, text="")  # Remove text
            self.map_label.image = self.image_reference

    def start_deployment(self):
        if not self.map_image:
            return

        try:
            area_width = float(self.area_width_input.get())
            area_height = float(self.area_height_input.get())
            grid_size = float(self.grid_size_input.get())
            sensor_range = float(self.sensor_range_input.get())

            # Start the deployment in a separate thread
            self.deployment_thread = threading.Thread(
                target=self.deploy_sensors,
                args=(area_width, area_height, grid_size, sensor_range),
                daemon=True  # Ensure the thread doesn't prevent program exit
            )
            self.deployment_thread.start()
        except ValueError:
            print("Please enter valid numerical values.")

    def deploy_sensors(self, area_width, area_height, grid_size, sensor_range):
        map_image = self.map_image
        map_array = np.array(map_image)

        # Convert to HSV and create water mask
        map_hsv = cv2.cvtColor(map_array, cv2.COLOR_RGB2HSV)
        blue_lower = np.array([90, 50, 50])
        blue_upper = np.array([130, 255, 255])
        water_mask = cv2.inRange(map_hsv, blue_lower, blue_upper)

        # Scale factors
        scale_width = map_image.width / area_width
        scale_height = map_image.height / area_height

        # Grid points for sensor placement
        grid_points_x = np.arange(grid_size / 2, area_width, grid_size)
        grid_points_y = np.arange(grid_size / 2, area_height, grid_size)

        sensors = []
        processed_points = 0
        total_points = len(grid_points_x) * len(grid_points_y)

        # Deploy sensors with optimal placement strategy
        for x in grid_points_x:
            for y in grid_points_y:
                image_x = x * scale_width
                image_y = y * scale_height

                if (
                    0 <= int(image_y) < water_mask.shape[0]
                    and 0 <= int(image_x) < water_mask.shape[1]
                ):
                    if water_mask[int(image_y), int(image_x)] != 0:
                        valid_position = self.find_closest_valid_position((image_x, image_y), water_mask)
                        if valid_position:
                            sensors.append(valid_position)
                    else:
                        sensors.append((image_x, image_y))

                # Update progress
                processed_points += 1
                progress = int(100 * processed_points / total_points)
                self.progress_bar.set(progress / 100)

        # Show deployment results
        self.show_deployment_results(sensors, sensor_range, scale_width)

    def find_closest_valid_position(self, position, mask):
        """Find the nearest valid position using a bounded breadth-first search."""
        directions = [
            (dx, dy)
            for dx in range(-10, 11)
            for dy in range(-10, 11)
        ]
        queue = deque([position])
        visited = set()  # To avoid redundant checks

        while queue:
            current_x, current_y = queue.popleft()

            if (
                0 <= int(current_y) < mask.shape[0]
                and 0 <= int(current_x) < mask.shape[1]
                and (current_x, current_y) not in visited
            ):
                visited.add((current_x, current_y))

                if mask[int(current_y), int(current_x)] == 0:
                    return (current_x, current_y)

                # Enqueue adjacent positions
                for dx, dy in directions:
                    queue.append((current_x + dx, current_y + dy))

        return None  # No valid position found within the search radius

    def show_deployment_results(self, sensors, sensor_range, scale_width):
        # Display the sensor deployment
        fig, ax = plt.subplots()

        map_array = np.array(self.map_image)
        ax.imshow(map_array)

        for x, y in sensors:
            ax.scatter(x, y, c='red', zorder=2)

            sensor_circle = patches.Circle(
                (x, y),
                radius=sensor_range * scale_width,
                color='red',
                alpha=0.2,
                zorder=1
            )
            ax.add_patch(sensor_circle)

        ax.axis('off')
        plt.show()

        # Plot sensor distribution
        self.plot_sensor_distribution(sensors)

    def plot_sensor_distribution(self, sensors):
        # Create a histogram to show the distribution of sensors
        fig, ax = plt.subplots()
        ax.hist(
            [x for x, y in sensors],
            bins=int(float(self.grid_size_input.get())),
            alpha=0.7,
            label="X Distribution"
        )
        ax.hist(
            [y for x, y in sensors],
            bins=int(float(self.grid_size_input.get())),
            alpha=0.7,
            label="Y Distribution"
        )
        ax.set_xlabel("Location")
        ax.set_ylabel("Sensor Count")
        ax.set_title("Sensor Distribution")
        ax.legend()

        plt.show()


# Run the application
if __name__ == "__main__":
    app = SensorDeploymentApp()
    app.mainloop()
