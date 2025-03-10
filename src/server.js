import express from 'express';
import dotenv from 'dotenv';
import connectDB from './config/db.js';
import path from 'path';
import session from 'express-session';
import flash from 'connect-flash';
import User from './user.js';

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
        req.session.user = { id: patient._id.toString(), fullname: patient.fullname, role: "patient" };

        res.json({ success: true });
    } catch (error) {
        console.error("❌ Patient login error:", error);
        res.status(500).json({ success: false, message: "Server error." });
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
