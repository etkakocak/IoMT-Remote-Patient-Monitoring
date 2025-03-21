import mongoose from "mongoose";

const bloodPressureSchema = new mongoose.Schema({
    thepatient: { type: String, required: true }, 
    PTT: { type: Number, required: true }, 
    createdAt: { type: Date, default: Date.now } 
});

const BloodPressure = mongoose.model("BloodPressure", bloodPressureSchema);
export default BloodPressure;
