import React, { useState, useEffect, useCallback } from 'react';
import { Lightbulb, Send, Loader, ArrowRight } from 'lucide-react';
import FeynmanPractice from './FeynmanPractice.jsx';

// URL base de tu backend FastAPI (Debe ser accesible)
const API_BASE_URL = "http://127.0.0.1:8000/api";

// Componente individual para mostrar una Flashcard
const Flashcard = ({ question, answer, index }) => {
  const [isFlipped, setIsFlipped] = useState(false);

  return (
    <div 
      className="perspective-1000 w-full h-80 sm:h-96" 
      onClick={() => setIsFlipped(!isFlipped)}
    >
      <div 
        className={`relative w-full h-full transition-transform duration-700 shadow-xl rounded-2xl cursor-pointer ${isFlipped ? 'rotate-y-180' : ''}`}
        style={{ transformStyle: 'preserve-3d' }}
      >
        {/* Lado Frontal (Pregunta) */}
        <div 
          className="absolute w-full h-full bg-indigo-600/90 text-white rounded-2xl flex flex-col justify-center items-center p-8 backface-hidden"
          style={{ backfaceVisibility: 'hidden' }}
        >
          <span className="text-4xl font-extrabold mb-4 opacity-70">{index + 1}</span>
          <h2 className="text-2xl font-bold text-center">
            {question}
          </h2>
          <p className="absolute bottom-4 text-sm opacity-80">
            Haz clic para ver la respuesta
          </p>
        </div>

        {/* Lado Trasero (Respuesta) */}
        <div 
          className="absolute w-full h-full bg-white text-gray-800 rounded-2xl flex flex-col justify-start items-center p-8 rotate-y-180 overflow-y-auto shadow-inner"
          style={{ backfaceVisibility: 'hidden' }}
        >
          <h3 className="text-lg font-semibold mb-2 text-indigo-700">Respuesta:</h3>
          <p className="text-base text-center">{answer}</p>
        </div>
      </div>
    </div>
  );
};

// Componente Principal de la Aplicación
const App = () => {
  const [materialId, setMaterialId] = useState(4); // ID predeterminado de la prueba
  const [query, setQuery] = useState('Create study flashcards on key concepts');
  const [flashcards, setFlashcards] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchFlashcards = useCallback(async () => {
    if (!materialId || !query) {
      setError('Por favor, ingresa un ID de material y una consulta.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setFlashcards([]);

    try {
      const url = `${API_BASE_URL}/material/${materialId}/generate_flashcards`;
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: query }),
      });

      if (!response.ok) {
        throw new Error(`Error en la API: ${response.statusText}`);
      }

      const result = await response.json();
      
      if (result.flashcards && result.flashcards.flashcards) {
        setFlashcards(result.flashcards.flashcards);
      } else {
        setError("La IA no devolvió flashcards en el formato esperado.");
      }
    } catch (err) {
      console.error(err);
      setError(`Fallo al conectar con el backend: ${err.message}. Asegúrate de que el servidor FastAPI esté corriendo en ${API_BASE_URL}.`);
    } finally {
      setIsLoading(false);
    }
  }, [materialId, query]);

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-8 font-sans">
      <header className="max-w-4xl mx-auto mb-8">
        <h1 className="text-4xl font-extrabold text-indigo-800 flex items-center mb-2">
          <Lightbulb className="mr-3 h-8 w-8 text-yellow-500" />
          estudIA: RAG Flashcards
        </h1>
        <p className="text-gray-600">
          Genera fichas de estudio personalizadas a partir del material subido (ID: {materialId}).
        </p>
      </header>

      {/* Controles de Entrada */}
      <main className="max-w-4xl mx-auto bg-white p-6 sm:p-8 rounded-xl shadow-2xl">
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4 mb-6">
          <div className="md:col-span-1">
            <label htmlFor="materialId" className="block text-sm font-medium text-gray-700">
              Material ID
            </label>
            <input
              id="materialId"
              type="number"
              value={materialId}
              onChange={(e) => setMaterialId(parseInt(e.target.value) || '')}
              className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm p-3 focus:border-indigo-500 focus:ring-indigo-500 transition"
              placeholder="Ej: 4"
            />
          </div>
          <div className="md:col-span-5">
            <label htmlFor="query" className="block text-sm font-medium text-gray-700">
              Consulta de Generación
            </label>
            <div className="flex mt-1">
              <input
                id="query"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="flex-grow rounded-l-lg border-gray-300 shadow-sm p-3 focus:border-indigo-500 focus:ring-indigo-500 transition border-r-0"
                placeholder="Ej: Crea un quiz de 5 preguntas sobre la sincronización POSIX"
              />
              <button
                onClick={fetchFlashcards}
                disabled={isLoading}
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-6 rounded-r-lg shadow-md transition duration-200 disabled:bg-indigo-400 flex items-center"
              >
                {isLoading ? (
                  <Loader className="animate-spin h-5 w-5 mr-2" />
                ) : (
                  <Send className="h-5 w-5 mr-2" />
                )}
                Generar
              </button>
            </div>
          </div>
        </div>

        {/* Estado de Carga / Error */}
        {isLoading && (
          <div className="flex items-center justify-center p-8 text-indigo-600">
            <Loader className="animate-spin h-6 w-6 mr-3" />
            <span className="text-lg font-medium">Buscando y Generando con Gemini...</span>
          </div>
        )}

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 p-4 rounded-lg my-4" role="alert">
            <p className="font-bold">Error:</p>
            <p>{error}</p>
          </div>
        )}

        {/* Resultados de Flashcards */}
        {flashcards.length > 0 && (
          <div className="mt-8">
            <h2 className="text-2xl font-bold text-gray-800 mb-6 border-b pb-2 flex items-center">
              <ArrowRight className="h-5 w-5 mr-2 text-indigo-500" />
              Fichas Generadas ({flashcards.length})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {flashcards.map((card, index) => (
                <Flashcard key={index} question={card.question} answer={card.answer} index={index} />
              ))}
            </div>
          </div>
        )}
        
        {/* Mensaje si no hay resultados */}
        {!isLoading && !error && flashcards.length === 0 && (
          <div className="text-center p-8 text-gray-500 bg-gray-50 rounded-lg">
            <p className="text-lg">¡Haz tu primera consulta RAG! Ingresa un ID de material y una pregunta (ejemplo: "Crea flashcards de las conclusiones").</p>
          </div>
        )}

        {/* Componente Feynman Practice integrado */}
        <FeynmanPractice defaultMaterialId={materialId} />

      </main>
      <footer className="max-w-4xl mx-auto mt-8 text-center text-gray-400 text-sm">
        estudIA - Desarrollado con FastAPI y Gemini RAG.
      </footer>
    </div>
  );
};

export default App;