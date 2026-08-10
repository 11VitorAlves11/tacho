import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { AddRecipe } from './pages/AddRecipe'
import { CookMode } from './pages/CookMode'
import { EditRecipe } from './pages/EditRecipe'
import { Home } from './pages/Home'
import { Login } from './pages/Login'
import { MealPlan } from './pages/MealPlan'
import { RecipeDetail } from './pages/RecipeDetail'
import { Setup } from './pages/Setup'
import { ShoppingList } from './pages/ShoppingList'

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}

function AppRoutes() {
  const { user, needsSetup } = useAuth()

  // undefined = ainda a verificar GET /users/me — evita um flash do ecrã de
  // login antes de sabermos se já há sessão válida.
  if (user === undefined || needsSetup === undefined) return null

  if (user === null) {
    if (needsSetup) {
      return (
        <Routes>
          <Route path="/setup" element={<Setup />} />
          <Route path="*" element={<Navigate to="/setup" replace />} />
        </Routes>
      )
    }
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/setup" element={<Setup />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/adicionar" element={<AddRecipe />} />
      <Route path="/receitas/:id" element={<RecipeDetail />} />
      <Route path="/receitas/:id/editar" element={<EditRecipe />} />
      <Route path="/receitas/:id/cozinhar" element={<CookMode />} />
      <Route path="/planeamento" element={<MealPlan />} />
      <Route path="/lista-compras" element={<ShoppingList />} />
      <Route path="/login" element={<Navigate to="/" replace />} />
      <Route path="/setup" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
