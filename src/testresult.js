import mongoose from 'mongoose';

const TestResultSchema = new mongoose.Schema({
    thepatient: { type: String, required: true }, // Hasta UID'si
    result: { type: Number, required: true }, // Ölçülen değer
    testType: { type: String, required: true }, // Testin tipi (örneğin: 'bodytemp')
    createdAt: { type: Date, default: Date.now } // Zaman damgası
});

const TestResult = mongoose.model('TestResult', TestResultSchema);
export default TestResult;
