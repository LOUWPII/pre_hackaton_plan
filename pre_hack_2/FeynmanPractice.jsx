import React, { useState, useRef } from 'react';
import { Mic, StopCircle, Play } from 'lucide-react';

const API_BASE_URL = "http://127.0.0.1:8000/api";

export default function FeynmanPractice({ defaultMaterialId = 4 }) {
  const [materialId, setMaterialId] = useState(defaultMaterialId);
  const [topic, setTopic] = useState('Tema');
  const [transcript, setTranscript] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [loading, setLoading] = useState(false);
  const recognitionRef = useRef(null);

  const supportsSTT = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition);
  const supportsTTS = typeof window !== 'undefined' && typeof window.speechSynthesis !== 'undefined';

  function startRecognition() {
    if (!supportsSTT) return alert('STT no soportado en este navegador. Usa la opción de escribir tu explicación.');

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SpeechRecognition();
    rec.lang = 'es-ES';
    rec.interimResults = false;
    rec.maxAlternatives = 1;

    rec.onstart = () => {
      setIsRecording(true);
      setTranscript('');
    };

    rec.onresult = (event) => {
      const text = event.results[0][0].transcript;
      setTranscript(text);
      setIsRecording(false);
      rec.stop();
      recognitionRef.current = null;
    };

    rec.onerror = (e) => {
      console.error('Speech recognition error', e);
      setIsRecording(false);
      recognitionRef.current = null;
      alert('Error al reconocer voz: ' + e.error);
    };

    rec.onend = () => {
      setIsRecording(false);
      recognitionRef.current = null;
    };

    recognitionRef.current = rec;
    rec.start();
  }

  function stopRecognition() {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) { }
      recognitionRef.current = null;
    }
    setIsRecording(false);
  }

  async function sendForFeedback() {
    if (!materialId) return alert('Proporciona un materialId válido');
    if (!transcript || transcript.trim().length < 5) return alert('Explica algo de al menos 5 caracteres o usa el mic.');

    setLoading(true);
    setFeedback('');

    try {
      const url = `${API_BASE_URL}/material/${materialId}/feynman_feedback?topic=${encodeURIComponent(topic)}`;
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_explanation: transcript })
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(`${resp.status} ${txt}`);
      }

      const data = await resp.json();
      setFeedback(data.feedback || 'No se recibió feedback.');

      // reproduce con TTS si está disponible
      if (supportsTTS && data.feedback) {
        const utter = new SpeechSynthesisUtterance(data.feedback);
        utter.lang = 'es-ES';
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utter);
      }

    } catch (err) {
      console.error('Error requesting feynman feedback', err);
      alert('Error al solicitar feedback: ' + err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto bg-white p-6 sm:p-8 rounded-xl shadow-2xl mt-8">
      <h2 className="text-2xl font-bold text-gray-800 mb-4">Práctica Técnica de Feynman</h2>

      <div className="grid grid-cols-1 md:grid-cols-6 gap-4 mb-4">
        <div className="md:col-span-1">
          <label className="block text-sm font-medium text-gray-700">Material ID</label>
          <input type="number" value={materialId} onChange={(e) => setMaterialId(parseInt(e.target.value)||'')}
            className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm p-3" />
        </div>
        <div className="md:col-span-5">
          <label className="block text-sm font-medium text-gray-700">Tema (opcional)</label>
          <input type="text" value={topic} onChange={(e) => setTopic(e.target.value)}
            className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm p-3" />
        </div>
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">Tu explicación (voz o texto)</label>

        <div className="flex gap-2 mb-2">
          <button onClick={() => isRecording ? stopRecognition() : startRecognition()}
            className={`inline-flex items-center px-4 py-2 rounded-lg font-semibold ${isRecording ? 'bg-red-500 text-white' : 'bg-indigo-600 text-white'}`}>
            {isRecording ? <StopCircle className="mr-2" /> : <Mic className="mr-2" />} {isRecording ? 'Detener' : 'Grabar'}
          </button>
          <button onClick={() => { setTranscript(''); setFeedback(''); }}
            className="inline-flex items-center px-4 py-2 rounded-lg bg-gray-200">
            Limpiar
          </button>
        </div>

        <textarea value={transcript} onChange={(e) => setTranscript(e.target.value)} rows={5}
          className="w-full rounded-lg border-gray-200 p-3 shadow-inner" placeholder={supportsSTT ? 'Pulsa Grabar y habla, o pega tu explicación aquí.' : 'Tu navegador no soporta reconocimiento de voz. Escribe tu explicación aquí.'} />
      </div>

      <div className="flex items-center gap-3">
        <button onClick={sendForFeedback} disabled={loading}
          className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-6 rounded-lg shadow-md disabled:opacity-60">
          {loading ? 'Generando feedback...' : 'Enviar y obtener feedback'}
        </button>
        {supportsTTS ? (
          <span className="text-sm text-gray-500">Feedback será reproducido por tu navegador.</span>
        ) : (
          <span className="text-sm text-yellow-600">TTS no soportado en este navegador — feedback aparecerá en texto.</span>
        )}
      </div>

      {feedback && (
        <div className="mt-6 bg-gray-50 p-4 rounded-lg border">
          <h3 className="font-semibold mb-2">Feedback</h3>
          <p className="whitespace-pre-line">{feedback}</p>
        </div>
      )}
    </div>
  );
}
