import mongoose from 'mongoose';

const EKGResultSchema = new mongoose.Schema({
    thepatient: { type: String, required: true },
    result: [{ type: Number, required: true }],  
    testType: { type: String, required: true },
    createdAt: { type: Date, default: Date.now }
});

const EKGResult = mongoose.model('EKGResult', EKGResultSchema);
export default EKGResult;