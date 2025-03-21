import mongoose from 'mongoose';

const TestResultSchema = new mongoose.Schema({
    thepatient: { type: String, required: true }, 
    result: { type: Number, required: true }, 
    testType: { type: String, required: true }, 
    createdAt: { type: Date, default: Date.now } 
});

const TestResult = mongoose.model('TestResult', TestResultSchema);
export default TestResult;
