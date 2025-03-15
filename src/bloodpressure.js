import mongoose from "mongoose";

const bloodPressureSchema = new mongoose.Schema({
    thepatient: { type: String, required: true }, // Hasta UID'si
    PTT: { type: Number, required: true }, // Ölçülen değer
    createdAt: { type: Date, default: Date.now } // Zaman damgası
});

const BloodPressure = mongoose.model("BloodPressure", bloodPressureSchema);
export default BloodPressure;
