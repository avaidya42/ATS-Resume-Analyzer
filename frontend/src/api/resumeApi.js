import axios from 'axios';

const client = axios.create({ baseURL: 'http://localhost:8000/api' });

// 1. Upload Resume File (Phase 1)
export async function uploadResume(file) {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await client.post('/resume/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

// 2. Analyze Job Description Match (Phase 2)
export async function analyzeJd(resumeText, jdText) {
  const { data } = await client.post('/resume/analyze-jd', {
    resume_text: resumeText,
    jd_text: jdText,
  });
  return data;
}

// 3. Optimize Bullet Point with Gemini (Phase 2)
export async function optimizeBullet(bulletPoint, targetJd = '') {
  const { data } = await client.post('/resume/optimize-bullet', {
    bullet_point: bulletPoint,
    target_jd: targetJd,
  });
  return data;
}
