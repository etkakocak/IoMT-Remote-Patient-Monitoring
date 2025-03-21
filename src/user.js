import mongoose from 'mongoose';
import bcrypt from 'bcryptjs';

const userSchema = new mongoose.Schema({
    username: { type: String, required: true, unique: true },
    password: { type: String },
    fullname: { type: String, required: true },
    role: { type: String, enum: ['healthcare', 'patient'], required: true },
    uid: { type: String, unique: true, sparse: true }, // Patient tag UID
    age: { type: Number },
    gender: { type: String, enum: ['Male', 'Female'] },
    smoking: { type: String, enum: ['Yes', 'No'] },
    exercise: { type: String, enum: ['Yes', 'No'] },
    hypertension: { type: String, enum: ['Yes', 'No'] },
    bloodpressure: { type: String, enum: ['Low', 'Normal', 'High'] }
});

// Password hashing
userSchema.pre('save', async function (next) {
    if (!this.isModified('password') || !this.password) return next();
    const salt = await bcrypt.genSalt(10);
    this.password = await bcrypt.hash(this.password, salt);
    next();
});

userSchema.methods.matchPassword = async function (enteredPassword) {
    return await bcrypt.compare(enteredPassword, this.password);
};

const User = mongoose.model('User', userSchema);
export default User;
