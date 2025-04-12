# Remote Patient Monitoring

This project is a full-stack web-based Remote Patient Monitoring (RPM) system that integrates a custom-built hardware device with biomedical sensors and a Node.js web application. Patients can measure key health parameters including body temperature, SpO₂, ECG, and systolic blood pressure using the device. Results are securely transmitted to a server, stored in a database, and displayed to both patients and healthcare professionals through a user-friendly web interface.   

## Structure

``/RPI``: Contains the MicroPython scripts running on the Raspberry Pi Pico W for sensor data collection and device-side communication.  
``/public``: Frontend static assets of the web application, including images, custom CSS, and client-side JavaScript used by the web interface.  
``/src``: Backend logic of the web application, implemented using Node.js and Express.js, including route handlers and API logic.  
``/view``: EJS (Embedded JavaScript) templates used for rendering dynamic frontend pages.  

## Key Features
- NFC-based patient login
- Real-time sensor data transmission using HTTP protocol
- Role-based authorization for patients and healthcare professionals
- Sensor data visualization and test history tracking
- Modular and scalable backend using Node.js, Express.js, and MongoDB

## Documentation
The complete academic report, covering the design, technical implementation, and other aspects of the system, is available:  
👉 [Remote Patient Monitoring - Final Report](./documentation)