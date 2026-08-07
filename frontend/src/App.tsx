import { Route, Routes } from 'react-router-dom'
import { AddRecipe } from './pages/AddRecipe'
import { CookMode } from './pages/CookMode'
import { EditRecipe } from './pages/EditRecipe'
import { Home } from './pages/Home'
import { RecipeDetail } from './pages/RecipeDetail'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/adicionar" element={<AddRecipe />} />
      <Route path="/receitas/:id" element={<RecipeDetail />} />
      <Route path="/receitas/:id/editar" element={<EditRecipe />} />
      <Route path="/receitas/:id/cozinhar" element={<CookMode />} />
    </Routes>
  )
}
