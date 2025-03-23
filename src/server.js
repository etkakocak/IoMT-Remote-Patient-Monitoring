import express from 'express';
import dotenv from 'dotenv';
import connectDB from './config/db.js';
import path from 'path';
import session from 'express-session';
import flash from 'connect-flash';
import User from './user.js';
import TestResult from './testresult.js';
import EKGResult from './EKGresult.js';
import BloodPressure from "./bloodpressure.js";
import { spawn } from "child_process";

dotenv.config();
connectDB();

const app = express();

// EJS Template Engine 
app.set('view engine', 'ejs');
app.set('views', path.join(path.resolve(), 'view'));

app.use(express.static(path.join(path.resolve(), 'public')));

// Middlewares
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(session({
    secret: process.env.SESSION_SECRET || 'supersecret',
    resave: false,
    saveUninitialized: true
}));
app.use(flash());

// Flash Messages
app.use((req, res, next) => {
    res.locals.success_msg = req.flash('success_msg');
    res.locals.error_msg = req.flash('error_msg');
    res.locals.user = req.session.user || null;
    next();
});

app.get('/', (req, res) => {
    res.render('index');
});

app.get('/healthcare-login', (req, res) => {
    res.render('healthcare-login');
});

app.get('/patient-login', (req, res) => {
    res.render('patient-login');
});

app.get('/register', (req, res) => {
    res.render('register');
});

app.post('/auth/healthcare-login', async (req, res) => {
    const { username, password } = req.body;

    try {
        const user = await User.findOne({ username });

        if (!user || !(await user.matchPassword(password))) {
            req.flash('error_msg', 'Invalid username or password');
            return res.redirect('/healthcare-login');
        }

        if (user.role !== 'healthcare') {
            req.flash('error_msg', 'Access denied. This login is for healthcare professionals only.');
            return res.redirect('/healthcare-login');
        }

        req.session.user = { id: user._id.toString(), fullname: user.fullname.toString(), username: user.username, role: user.role };
        req.flash('success_msg', `Login successful! Welcome, ${user.fullname}.`);
        res.redirect('/dashboard');
    } catch (error) {
        console.error("❌ Server Error:", error);
        req.flash('error_msg', 'Server error');
        res.redirect('/healthcare-login');
    }
});

app.post('/auth/patient-login', async (req, res) => {
    const { uid } = req.body;

    if (!uid) {
        return res.json({ success: false, message: "No tag detected." });
    }

    try {
        const patient = await User.findOne({ username: uid, role: "patient" });

        if (!patient) {
            return res.json({ success: false, message: "Invalid patient card." });
        }

        req.session.user = { id: patient._id.toString(), fullname: patient.fullname, username: patient.username, role: "patient" };

        res.json({ success: true });

        console.log("🔍 Session:", req.session.user?.username);
    } catch (error) {
        console.error("❌ Patient login error:", error);
        res.status(500).json({ success: false, message: "Server error." });
    }
});

app.get('/api/test-history', async (req, res) => {
    if (!req.session.user) {
        return res.status(401).json({ success: false, message: "Unauthorized" });
    }

    try {
        const patientUID = req.session.user.username;

        const history = await TestResult.find({ thepatient: patientUID }).sort({ createdAt: -1 });

        res.json({ success: true, history });
    } catch (error) {
        console.error("❌ Error:", error);
        res.status(500).json({ success: false, message: "Database error." });
    }
});

let scanRequestActive = false;
let lastScannedUID = null;

// Endpoint Running When Scan Button Is Pressed
app.post('/api/scan-card', (req, res) => {
    scanRequestActive = true; 
    lastScannedUID = null; 
    res.json({ success: true, message: "Scanning started." });

    setTimeout(() => {
        if (!lastScannedUID) {
            scanRequestActive = false;
        }
    }, 3000);
});

app.get('/api/scan-card', async (req, res) => {
    if (scanRequestActive) {
        res.json('SCAN');
        scanRequestActive = false;
    } else {
        res.json({ success: false });
    }
});

app.get('/api/get-latest-tag', (req, res) => {
    if (lastScannedUID) {
        res.json({ uid: lastScannedUID });
        lastScannedUID = null; 
    } else {
        res.json({ uid: null });
    }
});

app.post('/api/send-tag', (req, res) => {
    const { uid } = req.body;

    if (!uid) {
        return res.status(400).json({ success: false, message: "No UID provided." });
    }

    console.log(`Tag from Rpi: ${uid}`);
    
    lastScannedUID = uid; 
    res.json({ success: true, message: `Tag received: ${uid}` });
});

let btRequestActive = false;
let lastMeasuredTemp = null;
let pendingMeasurementForUser = null;

app.post('/api/measure-bodytemp', (req, res) => {
    if (!req.session.user) {
        return res.json({ success: false, message: "Not logged in" });
    } else {
        pendingMeasurementForUser = req.session.user.username;
    }

    console.log("🔄 The website launched body temperature measurement...");
    
    if (btRequestActive) {
        return res.json({ success: false, message: "Measurement already in progress." });
    }

    btRequestActive = true; 
    lastMeasuredTemp = null; 

    res.json({ success: true, message: "Measurement started." });
});

app.get('/api/measure-bodytemp', (req, res) => {
    if (btRequestActive) {
        res.json("measure"); 
    } else {
        res.json({ success: false, message: "No active measurement request." });
    }
});

app.post('/api/store-bodytemp', async (req, res) => {
    const { temperature } = req.body; 

    const patientUID = pendingMeasurementForUser; 

    console.log(`✅ Bodytemp: ${temperature}°C, Patient: ${patientUID}`);

    if (!patientUID) {
        console.error("❌ Patient UID not found!");
        return res.status(400).json({ success: false, message: "Patient UID is missing." });
    }

    try {
        const newTest = new TestResult({
            thepatient: patientUID, 
            result: temperature, 
            testType: "bodytemp"
        });

        await newTest.save();
        console.log("✅ Test sonucu veritabanına kaydedildi!");

        lastMeasuredTemp = temperature;
        btRequestActive = false;

        res.json({ success: true, message: "Measurement recorded.", temperature: lastMeasuredTemp });
    } catch (error) {
        console.error("❌ Error:", error);
        res.status(500).json({ success: false, message: "Database error." });
    }
});

app.get('/api/get-bodytemp', (req, res) => {
    console.log("The web page queried the measurement result...");
    if (lastMeasuredTemp !== null) {
        console.log(`✅ Bodytemp: ${lastMeasuredTemp}°C`);
        res.json({ success: true, temperature: lastMeasuredTemp });
        lastMeasuredTemp = null; 
    } else {
        console.log("❌ No result found.");
        res.json({ success: false, message: "Measurement failed or not completed yet." });
    }
});

let spo2RequestActive = false;
let lastMeasuredSpo2 = null;
let pendingSpo2MeasurementForUser = null;

app.post('/api/measure-spo2', (req, res) => {
    if (!req.session.user) {
        return res.json({ success: false, message: "Not logged in" });
    } else {
        pendingSpo2MeasurementForUser = req.session.user.username;
    }

    console.log("🔄 The website launched SpO₂ measurement...");
    
    if (spo2RequestActive) {
        return res.json({ success: false, message: "SpO₂ measurement already in progress." });
    }

    spo2RequestActive = true; 
    lastMeasuredSpo2 = null; 

    res.json({ success: true, message: "SpO₂ measurement started." });
});

app.get('/api/spo2', (req, res) => {
    if (spo2RequestActive) {
        res.json("spo2start"); 
    } else {
        res.json({ success: false, message: "No active SpO₂ measurement request." });
    }
});

app.post('/api/store-spo2', async (req, res) => {
    const { spo2 } = req.body; 

    const patientUID = pendingSpo2MeasurementForUser; 

    console.log(`✅ SpO₂ measurement: ${spo2}%, Patient: ${patientUID}`);

    if (!patientUID) {
        console.error("❌ Patient UID not found!");
        return res.status(400).json({ success: false, message: "Patient UID is missing." });
    }

    try {
        const newTest = new TestResult({
            thepatient: patientUID, 
            result: spo2, 
            testType: "spo2"
        });

        await newTest.save();
        console.log("✅ SpO₂ result saved to database!");

        lastMeasuredSpo2 = spo2;
        spo2RequestActive = false;

        res.json({ success: true, message: "SpO₂ measurement recorded.", spo2: lastMeasuredSpo2 });
    } catch (error) {
        console.error("❌ SpO₂ saving error:", error);
        res.status(500).json({ success: false, message: "Database error." });
    }
});

app.get('/api/get-spo2', (req, res) => {
    console.log("📡 The website queried the SpO₂ measurement result...");
    if (lastMeasuredSpo2 !== null) {
        console.log(`✅ SpO₂ from server: ${lastMeasuredSpo2}%`);
        res.json({ success: true, spo2: lastMeasuredSpo2 });
        lastMeasuredSpo2 = null; 
    } else {
        console.log("❌ SpO₂ result not found in server.");
        res.json({ success: false, message: "SpO₂ measurement failed or not completed yet." });
    }
});

let ekgRequestActive = false;
let lastMeasuredEKG = null;
let pendingEKGForUser = null;

app.post('/api/measure-ekg', (req, res) => {
    if (!req.session.user) {
        return res.json({ success: false, message: "Not logged in" });
    } else {
        pendingEKGForUser = req.session.user.username;
    }

    console.log("🔄 The website started EKG measurement...");

    if (ekgRequestActive) {
        return res.json({ success: false, message: "EKG measurement already in progress." });
    }

    ekgRequestActive = true; 
    lastMeasuredEKG = null; 

    res.json({ success: true, message: "EKG measurement started." });
});

app.get('/api/EKG', (req, res) => {
    if (ekgRequestActive) {
        res.json("EKGstart"); 
    } else {
        res.json({ success: false, message: "No active EKG request." });
    }
});

app.post('/api/store-EKG', async (req, res) => {
    const { EKG } = req.body;  
    const patientUID = pendingEKGForUser; 

    console.log("✅ Incoming data:", req.body);
    console.log(`✅ EKG data was obtained. Patient: ${patientUID}`);

    if (!patientUID) {
        console.error("❌ Patient UID not found!");
        return res.status(400).json({ success: false, message: "Patient UID is missing." });
    }

    try {
        const newTest = new EKGResult({
            thepatient: patientUID, 
            result: EKG, 
            testType: "ekg"
        });

        await newTest.save();
        console.log("✅ EKG data saved to database!");

        lastMeasuredEKG = EKG;
        ekgRequestActive = false;

        res.json({ success: true, message: "EKG recorded." });
    } catch (error) {
        console.error("❌ EKG saving error:", error);
        res.status(500).json({ success: false, message: "Database error." });
    }
});

app.get('/api/get-ekg', (req, res) => {
    console.log("📡 The website queried the EKG result...");
    
    if (lastMeasuredEKG !== null) {
        console.log("✅ EKG data from server:", lastMeasuredEKG);
        res.json({ success: true, ekg: lastMeasuredEKG });
        lastMeasuredEKG = null; 
    } else {
        console.log("❌ EKG result not found in server.");
        res.json({ success: false, message: "EKG measurement not ready yet." });
    }
});

app.get('/api/get-latest-ekg', async (req, res) => {
    if (!req.session.user) {
        return res.status(401).json({ success: false, message: "Not logged in" });
    }

    try {
        const latestEKGs = await EKGResult.find({ thepatient: req.session.user.username })
            .sort({ createdAt: -1 }) 
            .limit(5); 

        if (!latestEKGs.length) {
            return res.json({ success: false, message: "No EKG data found." });
        }

        res.json({ 
            success: true, 
            ekgResults: latestEKGs.map(test => ({
                id: test._id,
                ekg: test.result, 
                date: new Date(test.createdAt).toLocaleString()
            }))
        });
    } catch (error) {
        console.error("❌ Error fetching EKG data:", error);
        res.status(500).json({ success: false, message: "Database error." });
    }
});

let bpDataBuffer = [];
let pendingBPForUser = null;
let bpRequestActive = false; 
let latestPTT = null;

app.get("/api/BP", (req, res) => {
    if (bpRequestActive) {
        console.log("📡 RPi started BP measurement...");
        res.json("BPstart"); 
    } else {
        res.json({ success: false, message: "No active BP request." });
    }
});

app.post("/api/BP", (req, res) => {
    if (!req.session.user) {
        return res.json({ success: false, message: "Not logged in" });
    }

    if (bpRequestActive) {
        return res.json({ success: false, message: "BP measurement already in progress." });
    }

    pendingBPForUser = req.session.user.username;
    bpRequestActive = true; 

    console.log("🔄 BP measurement started...");
    res.json({ success: true, message: "BP measurement started." });
});

app.post("/api/live-bp", async (req, res) => {
    const bpData = req.body;

    if (!bpData || !bpData.timestamp || !bpData.max30102_ir || !bpData.icquanzx) {
        return res.status(400).json({ success: false, message: "Invalid BP data format" });
    }

    bpDataBuffer.push(bpData);

    if (bpDataBuffer.length >= 200) {  
        console.log("✅ Data received, calculating PTT...");
        
        try {
            const result = await processBPData(bpDataBuffer);  // wait until Python calc done
            console.log("✅ BP test done");
        } catch (err) {
            console.error("❌ BP test error:", err.message);
        }

        bpRequestActive = false;  
        pendingBPForUser = null;  
        bpDataBuffer = []; 
    }

    res.json({ success: true, message: "BP data received" });
});

function processBPData(sensorData) {
    return new Promise((resolve, reject) => {
        console.log("📡 Data sent to Python script:", JSON.stringify(sensorData));

        const pythonProcess = spawn("python", ["src/calculate_ptt.py"]);

        pythonProcess.stdin.write(JSON.stringify(sensorData));
        pythonProcess.stdin.end();

        let resultData = "";

        pythonProcess.stdout.on("data", (data) => {
            console.log("📡 Data from Python script:", data.toString());
            resultData += data.toString();
        });

        pythonProcess.stderr.on("data", (data) => {
            console.error(`❌ Python error: ${data}`);
        });

        pythonProcess.on("close", async () => {
            try {
                console.log("📡 Raw data:", resultData); // JSON raw data
                const output = JSON.parse(resultData);
            
                if (typeof output !== "object" || output === null) {
                    throw new Error("Invalid JSON format from Python script.");
                }
            
                console.log("✅ JSON Output:", output);
            
                if (!output.success) {  
                    console.warn(`⚠️ PTT could not be calculated: ${output.error}`);
                    return reject(new Error(output.error || "PTT could not be calculated"));
                }
            
                const patientUID = pendingBPForUser;
                if (!patientUID) {
                    console.error("❌ Patient UID not found!");
                    return reject(new Error("Patient UID not found."));
                }
            
                const newBPRecord = new BloodPressure({
                    thepatient: patientUID,
                    PTT: output.PTT,
                    date: new Date().toLocaleString()
                });
            
                await newBPRecord.save();
                console.log(`✅ PTT saved: ${output.PTT} ms`);
                latestPTT = output.PTT;
                return resolve({ success: true, PTT: output.PTT });
            
            } catch (err) {
                console.error("❌ JSON Parse error:", err.message);
                console.error("📡 Raw data:", resultData); 
                return reject(new Error("JSON error."));
            }            
        });
    });
}

app.get("/api/get-latest-bp", async (req, res) => {
    if (!req.session.user) {
        return res.status(401).json({ success: false, message: "Not logged in" });
    }

    if (bpRequestActive) { 
        return res.json({ success: false, message: "BP measurement in progress." });
    }

    if (latestPTT != null) { 
        console.log(`✅ PTT saved: ${latestPTT} ms`);
        res.json({ success: true });
    } else {
        console.error("❌ Error fetching BP data:");
        res.status(500).json({ success: false, message: "BP measurement error. Try again." });
    }
});

app.get("/api/get-patient-ptt", async (req, res) => {
    if (!req.session.user) {
        return res.status(401).json({ success: false, message: "Not logged in" });
    }

    try {
        const patientPTT = await BloodPressure.find({ thepatient: req.session.user.username })
            .sort({ createdAt: -1 }) 
        
        if (!patientPTT.length) {
            return res.json({ success: false, message: "No PTT data found." });
        }

        res.json({ success: true, pttRecords: patientPTT });
    } catch (error) {
        console.error("❌ Error fetching PTT data:", error);
        res.status(500).json({ success: false, message: "Database error." });
    }
});

app.get("/api/get-patient-info", async (req, res) => {
    if (!req.session.user) {
        return res.status(401).json({ success: false, message: "Not logged in" });
    }

    try {
        const patientInfo = await User.findOne({ username: req.session.user.username });

        if (!patientInfo) {
            return res.json({ success: false, message: "Patient info not found." });
        }

        res.json({ 
            success: true, 
            patient: {
                age: patientInfo.age,
                gender: patientInfo.gender,
                smoking: patientInfo.smoking,
                exercise: patientInfo.exercise,
                hypertension: patientInfo.hypertension,
                bloodpressure: patientInfo.bloodpressure
            }
        });

    } catch (error) {
        console.error("❌ Error fetching patient info:", error);
        res.status(500).json({ success: false, message: "Database error." });
    }
});

app.post('/auth/register', async (req, res) => {
    const { username, fullname, password, healthcareCode } = req.body;
    const VALID_HEALTHCARE_CODE = '2DT304'; // Valid code to register a healthcare professional.

    try {
        if (healthcareCode !== VALID_HEALTHCARE_CODE) {
            req.flash('error_msg', 'Invalid healthcare code.');
            return res.redirect('/register');
        }

        const userExists = await User.findOne({ username });
        if (userExists) {
            req.flash('error_msg', 'Username already exists.');
            return res.redirect('/register');
        }

        const newUser = new User({
            username,
            password,
            fullname,
            role: 'healthcare'
        });

        await newUser.save();

        req.session.user = { id: newUser._id.toString(), username: newUser.username, role: newUser.role };
        req.flash('success_msg', 'Registration successful! You are now logged in.');
        res.redirect('/dashboard');
    } catch (error) {
        console.error("❌ Server Error:", error);
        req.flash('error_msg', 'Server error.');
        res.redirect('/register');
    }
});

const requireHealthcare = (req, res, next) => {
    if (!req.session.user || req.session.user.role !== 'healthcare') {
        return res.status(403).render('error', { status: 403, error_msg: "Forbidden. You do not have permission to access this page." });
    }
    next();
};

app.get('/dashboard', requireHealthcare, (req, res) => {
    res.render('dashboard', { user: req.session.user });
});

app.get('/add-patient', requireHealthcare, (req, res) => {
    res.render('addpatient');
});

const requirePatient = (req, res, next) => {
    if (!req.session.user || req.session.user.role !== 'patient') {
        return res.status(403).render('error', { status: 403, error_msg: "Forbidden. You do not have permission to access this page." });
    }
    next();
};

app.get('/patient-dashboard', requirePatient, (req, res) => {
    res.render('patient', { user: req.session.user });
});

app.post('/add-patient', requireHealthcare, async (req, res) => {
    const { fullname, uid, age, gender, smoking, exercise, hypertension, bloodpressure } = req.body;

    if (!fullname || !uid || !age || !gender || !smoking || !exercise || !hypertension || !bloodpressure) {
        req.flash('error_msg', 'All fields are required!');
        return res.redirect('/add-patient');
    }

    try {
        // One tag is for only one patient.
        const existingPatient = await User.findOne({ uid, role: 'patient' });
        if (existingPatient) {
            req.flash('error_msg', 'A patient with this card ID already exists!');
            return res.redirect('/add-patient');
        }

        const newPatient = new User({
            username: uid, 
            fullname,
            password: uid, 
            role: 'patient',
            age,
            gender,
            smoking,
            exercise,
            hypertension,
            bloodpressure
        });

        await newPatient.save();

        req.flash('success_msg', 'Patient added successfully!');
        res.redirect('/dashboard');
    } catch (error) {
        console.error("❌ Error adding patient:", error);
        req.flash('error_msg', 'Server error. Please try again.');
        res.redirect('/add-patient');
    }
});

app.get('/api/all-patients', requireHealthcare, async (req, res) => {
    try {
        const patients = await User.find({ role: 'patient' }, 'fullname username'); 
        res.json({ success: true, patients });
    } catch (error) {
        console.error("❌ Error fetching patients:", error);
        res.status(500).json({ success: false, message: "Database error." });
    }
});

app.get('/api/test-history2/:patientUID', requireHealthcare, async (req, res) => {
    const { patientUID } = req.params;
    try {
        const history = await TestResult.find({ thepatient: patientUID }).sort({ createdAt: -1 });
        res.json({ success: true, history });
    } catch (error) {
        console.error("❌ Error fetching patient test history:", error);
        res.status(500).json({ success: false, message: "Database error." });
    }
});

app.get("/api/get-patient-ptt2/:patientUID", async (req, res) => {
    const { patientUID } = req.params;
    try {
        const patientPTT = await BloodPressure.find({ thepatient: patientUID })
            .sort({ createdAt: -1 }) 
        
        if (!patientPTT.length) {
            return res.json({ success: false, message: "No PTT data found." });
        }

        res.json({ success: true, pttRecords: patientPTT });
    } catch (error) {
        console.error("❌ Error fetching PTT data:", error);
        res.status(500).json({ success: false, message: "Database error." });
    }
});

app.get('/api/get-latest-ekg2/:patientUID', async (req, res) => {
    const { patientUID } = req.params;
    try {
        const latestEKGs = await EKGResult.find({ thepatient: patientUID })
            .sort({ createdAt: -1 }) 
            .limit(5); 

        if (!latestEKGs.length) {
            return res.json({ success: false, message: "No EKG data found." });
        }

        res.json({ 
            success: true, 
            ekgResults: latestEKGs.map(test => ({
                id: test._id,
                ekg: test.result, 
                date: new Date(test.createdAt).toLocaleString()
            }))
        });
    } catch (error) {
        console.error("❌ Error fetching EKG data:", error);
        res.status(500).json({ success: false, message: "Database error." });
    }
});

app.get("/api/get-patient-info2/:patientUID", async (req, res) => {
    const { patientUID } = req.params;

    try {
        const patientInfo = await User.findOne({ username: patientUID });

        if (!patientInfo) {
            return res.json({ success: false, message: "Patient info not found." });
        }

        res.json({ 
            success: true, 
            patient: {
                age: patientInfo.age,
                gender: patientInfo.gender,
                smoking: patientInfo.smoking,
                exercise: patientInfo.exercise,
                hypertension: patientInfo.hypertension,
                bloodpressure: patientInfo.bloodpressure
            }
        });

    } catch (error) {
        console.error("❌ Error fetching patient info:", error);
        res.status(500).json({ success: false, message: "Database error." });
    }
});

// To safe logout
app.get('/auth/logout', (req, res) => {
    if (!req.session.user) {
      return res.status(500).render('error', { status: 500, error_msg: 'Internal Server Error.' });
    }

    req.session.destroy(() => {
      res.redirect('/');
    });
});

// Start server.
const PORT = process.env.PORT || 5000;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`🚀 Server running on port ${PORT}`);
    console.log(`🌍 Visit the application at: http://localhost:${PORT}`);
});
