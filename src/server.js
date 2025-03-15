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

// 📌 EJS Template Engine Kullanımı
app.set('view engine', 'ejs');
app.set('views', path.join(path.resolve(), 'view'));

// 📌 Statik dosyaları kullan
app.use(express.static(path.join(path.resolve(), 'public')));

// 📌 Middleware'ler
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(session({
    secret: process.env.SESSION_SECRET || 'supersecret',
    resave: false,
    saveUninitialized: true
}));
app.use(flash());

// 📌 Flash Mesajlarını Template'e Aktarma
app.use((req, res, next) => {
    res.locals.success_msg = req.flash('success_msg');
    res.locals.error_msg = req.flash('error_msg');
    res.locals.user = req.session.user || null;
    next();
});

// 📌 Ana Sayfa
app.get('/', (req, res) => {
    res.render('index');
});

// 📌 Sağlık Çalışanı Girişi Sayfası
app.get('/healthcare-login', (req, res) => {
    res.render('healthcare-login');
});

// 📌 Hasta Girişi Sayfası (Kart Okutma ile Giriş)
app.get('/patient-login', (req, res) => {
    res.render('patient-login');
});

// 📌 Kullanıcı Kayıt Sayfası
app.get('/register', (req, res) => {
    res.render('register');
});

// 📌 ✅ **Sağlık Çalışanı Girişi (POST İşlemi)**
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

// ✅ **Patient Login (Tag ile Giriş)**
app.post('/auth/patient-login', async (req, res) => {
    const { uid } = req.body;

    if (!uid) {
        return res.json({ success: false, message: "No tag detected." });
    }

    try {
        // 🔥 **MongoDB'de UID'yi `username` alanında sakladığımız için burada `username` olarak arıyoruz.**
        const patient = await User.findOne({ username: uid, role: "patient" });

        if (!patient) {
            return res.json({ success: false, message: "Invalid patient card." });
        }

        // ✅ Kullanıcıyı oturum açmış hale getir
        req.session.user = { id: patient._id.toString(), fullname: patient.fullname, username: patient.username, role: "patient" };

        res.json({ success: true });

        console.log("🔍 Session içeriği:", req.session.user?.username);
    } catch (error) {
        console.error("❌ Patient login error:", error);
        res.status(500).json({ success: false, message: "Server error." });
    }
});

// ✅ **Hasta Test Geçmişini Getirme**
app.get('/api/test-history', async (req, res) => {
    if (!req.session.user) {
        return res.status(401).json({ success: false, message: "Unauthorized" });
    }

    try {
        const patientUID = req.session.user.username;

        // **Sadece bu hastaya ait testleri getiriyoruz**
        const history = await TestResult.find({ thepatient: patientUID }).sort({ createdAt: -1 });

        res.json({ success: true, history });
    } catch (error) {
        console.error("❌ Test geçmişi getirilirken hata oluştu:", error);
        res.status(500).json({ success: false, message: "Database error." });
    }
});

let scanRequestActive = false;
let lastScannedUID = null;

// ✅ Web Sayfası Scan Butonuna Basınca Çalışan Endpoint
app.post('/api/scan-card', (req, res) => {
    scanRequestActive = true; // ✅ RPi'nin kart okumasını başlatması için izin ver
    lastScannedUID = null; // 🔄 Önceki taramaları temizle
    res.json({ success: true, message: "Scanning started." });

    setTimeout(() => {
        if (!lastScannedUID) {
            scanRequestActive = false;
        }
    }, 3000);
});

// ✅ Raspberry Pi Tarama Başlatmasını Bekleyen Endpoint
app.get('/api/scan-card', async (req, res) => {
    if (scanRequestActive) {
        res.json('SCAN');
        scanRequestActive = false;
    } else {
        res.json({ success: false });
    }
});

// ✅ **Web Sayfası Tarafından Son Okunan UID'yi Kontrol Etme**
app.get('/api/get-latest-tag', (req, res) => {
    if (lastScannedUID) {
        res.json({ uid: lastScannedUID });
        lastScannedUID = null; // Kullanıldıktan sonra temizle
    } else {
        res.json({ uid: null });
    }
});

// ✅ **RPi, okuduğu kartı sunucuya POST eder**
app.post('/api/send-tag', (req, res) => {
    const { uid } = req.body;

    if (!uid) {
        return res.status(400).json({ success: false, message: "No UID provided." });
    }

    console.log(`✅ Raspberry Pi'den Yeni Kart Algılandı: ${uid}`);
    
    lastScannedUID = uid; // Son okutulan kartı kaydet
    res.json({ success: true, message: `Tag received: ${uid}` });
});

let btRequestActive = false;
let lastMeasuredTemp = null;
let pendingMeasurementForUser = null;

// ✅ **Hasta Web Sayfası "Başlat" Dediğinde Çalışan Endpoint**
app.post('/api/measure-bodytemp', (req, res) => {
    if (!req.session.user) {
        return res.json({ success: false, message: "Not logged in" });
    } else {
        pendingMeasurementForUser = req.session.user.username;
    }

    console.log("🔄 Web sayfası vücut sıcaklığı ölçümünü başlattı...");
    
    if (btRequestActive) {
        return res.json({ success: false, message: "Measurement already in progress." });
    }

    btRequestActive = true; // ✅ Testin başladığını kaydet
    lastMeasuredTemp = null; // Önceki veriyi temizle

    res.json({ success: true, message: "Measurement started." });
});

// ✅ **RPi'nin ölçüm isteğini aldığı endpoint**
app.get('/api/measure-bodytemp', (req, res) => {
    if (btRequestActive) {
        res.json("measure"); // 📡 RPi'ye "measure" komutunu gönder
    } else {
        res.json({ success: false, message: "No active measurement request." });
    }
});

app.post('/api/store-bodytemp', async (req, res) => {
    const { temperature } = req.body; 

    const patientUID = pendingMeasurementForUser; // 🔥 Hasta UID

    console.log(`✅ Vücut sıcaklığı ölçüldü: ${temperature}°C, Hasta: ${patientUID}`);

    if (!patientUID) {
        console.error("❌ Hasta UID bulunamadı! Session boş olabilir.");
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
        console.error("❌ Test sonucu kaydedilirken hata oluştu:", error);
        res.status(500).json({ success: false, message: "Database error." });
    }
});

// ✅ **Hasta Web Sayfası, ölçüm sonucunu almak için burayı çağırır**
app.get('/api/get-bodytemp', (req, res) => {
    console.log("📡 Web sayfası ölçüm sonucunu sorguladı...");
    if (lastMeasuredTemp !== null) {
        console.log(`✅ Sunucudan dönen sıcaklık: ${lastMeasuredTemp}°C`);
        res.json({ success: true, temperature: lastMeasuredTemp });
        lastMeasuredTemp = null; // Kullanıldıktan sonra sıfırla!
    } else {
        console.log("❌ Sunucuda ölçüm sonucu bulunamadı.");
        res.json({ success: false, message: "Measurement failed or not completed yet." });
    }
});

let spo2RequestActive = false;
let lastMeasuredSpo2 = null;
let pendingSpo2MeasurementForUser = null;

// ✅ **Hasta Web Sayfası "SpO2 Testi Başlat" Dediğinde Çalışan Endpoint**
app.post('/api/measure-spo2', (req, res) => {
    if (!req.session.user) {
        return res.json({ success: false, message: "Not logged in" });
    } else {
        pendingSpo2MeasurementForUser = req.session.user.username;
    }

    console.log("🔄 Web sayfası SpO₂ ölçümünü başlattı...");
    
    if (spo2RequestActive) {
        return res.json({ success: false, message: "SpO₂ measurement already in progress." });
    }

    spo2RequestActive = true; // ✅ Testin başladığını kaydet
    lastMeasuredSpo2 = null; // Önceki veriyi temizle

    res.json({ success: true, message: "SpO₂ measurement started." });
});

// ✅ **RPi'nin SpO₂ ölçüm isteğini aldığı endpoint**
app.get('/api/spo2', (req, res) => {
    if (spo2RequestActive) {
        res.json("spo2start"); // 📡 RPi'ye "SpO₂ ölçümüne başla" komutunu gönder
    } else {
        res.json({ success: false, message: "No active SpO₂ measurement request." });
    }
});

// ✅ **RPi'nin ölçtüğü SpO₂ verisini kaydettiği endpoint**
app.post('/api/store-spo2', async (req, res) => {
    const { spo2 } = req.body; 

    const patientUID = pendingSpo2MeasurementForUser; // 🔥 Hasta UID

    console.log(`✅ SpO₂ ölçüldü: ${spo2}%, Hasta: ${patientUID}`);

    if (!patientUID) {
        console.error("❌ Hasta UID bulunamadı! Session boş olabilir.");
        return res.status(400).json({ success: false, message: "Patient UID is missing." });
    }

    try {
        const newTest = new TestResult({
            thepatient: patientUID, 
            result: spo2, 
            testType: "spo2"
        });

        await newTest.save();
        console.log("✅ SpO₂ test sonucu veritabanına kaydedildi!");

        lastMeasuredSpo2 = spo2;
        spo2RequestActive = false;

        res.json({ success: true, message: "SpO₂ measurement recorded.", spo2: lastMeasuredSpo2 });
    } catch (error) {
        console.error("❌ SpO₂ test sonucu kaydedilirken hata oluştu:", error);
        res.status(500).json({ success: false, message: "Database error." });
    }
});

// ✅ **Hasta Web Sayfası, SpO₂ ölçüm sonucunu almak için burayı çağırır**
app.get('/api/get-spo2', (req, res) => {
    console.log("📡 Web sayfası SpO₂ ölçüm sonucunu sorguladı...");
    if (lastMeasuredSpo2 !== null) {
        console.log(`✅ Sunucudan dönen SpO₂: ${lastMeasuredSpo2}%`);
        res.json({ success: true, spo2: lastMeasuredSpo2 });
        lastMeasuredSpo2 = null; // Kullanıldıktan sonra sıfırla!
    } else {
        console.log("❌ Sunucuda SpO₂ ölçüm sonucu bulunamadı.");
        res.json({ success: false, message: "SpO₂ measurement failed or not completed yet." });
    }
});

let ekgRequestActive = false;
let lastMeasuredEKG = null;
let pendingEKGForUser = null;

// ✅ **Hasta Web Sayfası "Başlat" Dediğinde Çalışan Endpoint**
app.post('/api/measure-ekg', (req, res) => {
    if (!req.session.user) {
        return res.json({ success: false, message: "Not logged in" });
    } else {
        pendingEKGForUser = req.session.user.username;
    }

    console.log("🔄 Web sayfası EKG ölçümünü başlattı...");

    if (ekgRequestActive) {
        return res.json({ success: false, message: "EKG measurement already in progress." });
    }

    ekgRequestActive = true; 
    lastMeasuredEKG = null; 

    res.json({ success: true, message: "EKG measurement started." });
});

// ✅ **RPi'nin ölçüm isteğini aldığı endpoint**
app.get('/api/EKG', (req, res) => {
    if (ekgRequestActive) {
        res.json("EKGstart"); 
    } else {
        res.json({ success: false, message: "No active EKG request." });
    }
});

// ✅ **RPi'nin EKG verisini kaydettiği endpoint**
app.post('/api/store-EKG', async (req, res) => {
    const { EKG } = req.body;  
    const patientUID = pendingEKGForUser; // 🔥 **Session'dan UID al**

    console.log("✅ Gelen veri:", req.body);
    console.log(`✅ EKG verisi alındı. Hasta: ${patientUID}`);

    if (!patientUID) {
        console.error("❌ Hasta UID bulunamadı! Session boş olabilir.");
        return res.status(400).json({ success: false, message: "Patient UID is missing." });
    }

    try {
        const newTest = new EKGResult({
            thepatient: patientUID, 
            result: EKG, 
            testType: "ekg"
        });

        await newTest.save();
        console.log("✅ EKG verisi veritabanına kaydedildi!");

        lastMeasuredEKG = EKG;
        ekgRequestActive = false;

        res.json({ success: true, message: "EKG recorded." });
    } catch (error) {
        console.error("❌ EKG verisi kaydedilirken hata oluştu:", error);
        res.status(500).json({ success: false, message: "Database error." });
    }
});

// ✅ **Hasta Web Sayfası, EKG ölçüm sonucunu almak için burayı çağırır**
app.get('/api/get-ekg', (req, res) => {
    console.log("📡 Web sayfası EKG sonucunu sorguladı...");
    
    if (lastMeasuredEKG !== null) {
        console.log("✅ Sunucudan dönen EKG verisi:", lastMeasuredEKG);
        res.json({ success: true, ekg: lastMeasuredEKG });
        lastMeasuredEKG = null; // Kullanıldıktan sonra sıfırla!
    } else {
        console.log("❌ Sunucuda EKG sonucu bulunamadı, tekrar dene...");
        res.json({ success: false, message: "EKG measurement not ready yet." });
    }
});

app.get('/api/get-latest-ekg', async (req, res) => {
    if (!req.session.user) {
        return res.status(401).json({ success: false, message: "Not logged in" });
    }

    try {
        const latestEKGs = await EKGResult.find({ thepatient: req.session.user.username })
            .sort({ createdAt: -1 }) // En son kayıtları getir
            .limit(5); // Son 5 ölçümü getir

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
let bpRequestActive = false; // ✅ BP testi aktif mi?
let latestPTT = null;

// ✅ **RPi BP Ölçüm İsteğini Aldığında Yanıt Veren Endpoint**
app.get("/api/BP", (req, res) => {
    if (bpRequestActive) {
        console.log("📡 RPi BP ölçümünü başlatıyor...");
        res.json("BPstart"); // 🔥 **RPi'ye "BP ölçümünü başlat" komutu gidiyor**
    } else {
        res.json({ success: false, message: "No active BP request." });
    }
});

// ✅ **Hasta web sayfası BP ölçümü başlattığında çağrılan endpoint**
app.post("/api/BP", (req, res) => {
    if (!req.session.user) {
        return res.json({ success: false, message: "Not logged in" });
    }

    if (bpRequestActive) {
        return res.json({ success: false, message: "BP measurement already in progress." });
    }

    pendingBPForUser = req.session.user.username;
    bpRequestActive = true; // **Test başladı**

    console.log("🔄 BP ölçümü başlatıldı...");
    res.json({ success: true, message: "BP measurement started." });
});

// ✅ **RPi BP verisi gönderiyor**
app.post("/api/live-bp", async (req, res) => {
    const bpData = req.body;

    if (!bpData || !bpData.timestamp || !bpData.max30102_ir || !bpData.icquanzx) {
        return res.status(400).json({ success: false, message: "Invalid BP data format" });
    }

    bpDataBuffer.push(bpData);

    if (bpDataBuffer.length >= 200) {  // **Yeterli veri geldi mi?**
        console.log("✅ 200 veri alındı, PTT hesaplanıyor...");
        
        try {
            const result = await processBPData(bpDataBuffer);  // ✅ **Python script tamamlanana kadar bekle**
            console.log("✅ BP Testi başarıyla tamamlandı");
        } catch (err) {
            console.error("❌ BP testi başarısız:", err.message);
        }

        bpRequestActive = false;  // ✅ **Test tamamlandı**
        pendingBPForUser = null;  // ✅ **Hasta bilgisi sıfırlandı**
        bpDataBuffer = []; // ✅ **Listeyi temizle**
    }

    res.json({ success: true, message: "BP data received" });
});

// date: new Date(latestBP.createdAt).toLocaleString()
function processBPData(sensorData) {
    return new Promise((resolve, reject) => {
        console.log("📡 Python scriptine gönderilen veri:", JSON.stringify(sensorData));

        const pythonProcess = spawn("python", ["src/calculate_ptt.py"]);

        pythonProcess.stdin.write(JSON.stringify(sensorData));
        pythonProcess.stdin.end();

        let resultData = "";

        pythonProcess.stdout.on("data", (data) => {
            console.log("📡 Python scriptinden gelen veri:", data.toString());
            resultData += data.toString();
        });

        pythonProcess.stderr.on("data", (data) => {
            console.error(`❌ Python Hatası: ${data}`);
        });

        pythonProcess.on("close", async () => {
            try {
                console.log("📡 Alınan Ham Veri:", resultData); // ✅ JSON ham verisini logla
                const output = JSON.parse(resultData);
            
                // 🚨 Eğer JSON bir nesne değilse, hata ver
                if (typeof output !== "object" || output === null) {
                    throw new Error("Invalid JSON format from Python script.");
                }
            
                console.log("✅ JSON Çıktısı:", output);
            
                if (!output.success) {  // ✅ **Burada success kontrolü doğru yapılıyor**
                    console.warn(`⚠️ PTT hesaplanamadı: ${output.error}`);
                    return reject(new Error(output.error || "PTT ölçülemedi"));
                }
            
                const patientUID = pendingBPForUser;
                if (!patientUID) {
                    console.error("❌ Hasta UID bulunamadı!");
                    return reject(new Error("Hasta bilgisi eksik."));
                }
            
                // ✅ **MongoDB'ye kaydet**
                const newBPRecord = new BloodPressure({
                    thepatient: patientUID,
                    PTT: output.PTT,
                    date: new Date().toLocaleString()
                });
            
                await newBPRecord.save();
                console.log(`✅ PTT kaydedildi: ${output.PTT} ms`);
                latestPTT = output.PTT;
                return resolve({ success: true, PTT: output.PTT });
            
            } catch (err) {
                console.error("❌ JSON Parse Hatası:", err.message);
                console.error("📡 Alınan Ham Veri:", resultData); // ✅ JSON ham verisini logla
                return reject(new Error("PTT hesaplama hatası (JSON okunamadı)"));
            }            
        });
    });
}

// ✅ **Son BP ölçümünü getir**
app.get("/api/get-latest-bp", async (req, res) => {
    if (!req.session.user) {
        return res.status(401).json({ success: false, message: "Not logged in" });
    }

    if (bpRequestActive) { 
        return res.json({ success: false, message: "BP measurement in progress." });
    }

    if (latestPTT != null) { 
        console.log(`✅ PTT kaydedildi: ${latestPTT} ms`);
        res.json({ success: true });
    } else {
        console.error("❌ Error fetching BP data:");
        res.status(500).json({ success: false, message: "BP measurement error. Try again." });
    }
});


// 📌 ✅ **Sağlık Çalışanı Kayıt (POST İşlemi)**
app.post('/auth/register', async (req, res) => {
    const { username, fullname, password, healthcareCode } = req.body;
    const VALID_HEALTHCARE_CODE = '2DT304'; // Geçerli kod

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

// 📌 ✅ **Dashboard - Sadece Healthcare Kullanıcıları İçin**
const requireHealthcare = (req, res, next) => {
    if (!req.session.user || req.session.user.role !== 'healthcare') {
        return res.status(403).render('error', { status: 403, error_msg: "Forbidden. You do not have permission to access this page." });
    }
    next();
};

app.get('/dashboard', requireHealthcare, (req, res) => {
    res.render('dashboard', { user: req.session.user });
});

// 📌 ✅ **Hasta Ekleme Sayfası - Sadece Healthcare Kullanıcıları İçin**
app.get('/add-patient', requireHealthcare, (req, res) => {
    res.render('addpatient');
});

// 📌 ✅ **Hasta Paneli - Sadece Hasta Kullanıcıları İçin**
const requirePatient = (req, res, next) => {
    if (!req.session.user || req.session.user.role !== 'patient') {
        return res.status(403).render('error', { status: 403, error_msg: "Forbidden. You do not have permission to access this page." });
    }
    next();
};

app.get('/patient-dashboard', requirePatient, (req, res) => {
    res.render('patient', { user: req.session.user });
});

// ✅ **Yeni Hasta Ekleme İşlemi (POST)**
app.post('/add-patient', requireHealthcare, async (req, res) => {
    const { fullname, uid, age, gender, smoking, exercise, hypertension, bloodpressure } = req.body;

    // Eksik veri kontrolü
    if (!fullname || !uid || !age || !gender || !smoking || !exercise || !hypertension || !bloodpressure) {
        req.flash('error_msg', 'All fields are required!');
        return res.redirect('/add-patient');
    }

    try {
        // Zaten bu UID ile kayıtlı hasta var mı?
        const existingPatient = await User.findOne({ uid, role: 'patient' });
        if (existingPatient) {
            req.flash('error_msg', 'A patient with this card ID already exists!');
            return res.redirect('/add-patient');
        }

        // Yeni hasta kaydı oluştur
        const newPatient = new User({
            username: uid, // Kullanıcı adı olarak UID kullanılacak
            fullname,
            password: uid, // Şimdilik UID'yi şifre olarak atayalım (güvenlik açısından geliştirilebilir)
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


// 📌 ✅ **Çıkış (Logout) İşlemi**
app.get('/auth/logout', (req, res) => {
    if (!req.session.user) {
      return res.status(500).render('error', { status: 500, error_msg: 'Internal Server Error.' });
    }

    req.session.destroy(() => {
      res.redirect('/');
    });
});

// 📌 ✅ **Sunucuyu Başlat**
const PORT = process.env.PORT || 5000;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`🚀 Server running on port ${PORT}`);
    console.log(`🌍 Visit the application at: http://localhost:${PORT}`);
});
