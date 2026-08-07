import axios from 'axios'

// Em dev, o Vite corre no host e o backend é outro container/porta — sem
// proxy reverso comum ainda (isso é trabalho do deploy final no homelab),
// por isso a base URL vem de uma env var com fallback ao localhost:8000.
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
})
