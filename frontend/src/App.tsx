import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { AddRecipe } from './pages/AddRecipe'
import { CookbookDetail } from './pages/CookbookDetail'
import { Cookbooks } from './pages/Cookbooks'
import { CookMode } from './pages/CookMode'
import { EditRecipe } from './pages/EditRecipe'
import { ForwardAuthBlocked } from './pages/ForwardAuthBlocked'
import { Home } from './pages/Home'
import { Login } from './pages/Login'
import { MealPlan } from './pages/MealPlan'
import { Pantry } from './pages/Pantry'
import { PublicRecipe } from './pages/PublicRecipe'
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
  const { user, needsSetup, forwardAuthBlocked } = useAuth()
  const location = useLocation()

  // Única rota sem sessão nenhuma — link/QR gerado em "Partilhar"
  // (RecipeDetail.tsx). Tem de vir antes do gate de autenticação abaixo,
  // senão qualquer pessoa sem conta Tacho cairia sempre no login.
  if (location.pathname.startsWith('/partilha/')) {
    return (
      <Routes>
        <Route path="/partilha/:token" element={<PublicRecipe />} />
      </Routes>
    )
  }

  // undefined = ainda a verificar GET /users/me — evita um flash do ecrã de
  // login antes de sabermos se já há sessão válida.
  if (user === undefined || needsSetup === undefined) return null

  if (user === null) {
    if (needsSetup) {
      // Prioridade sobre forwardAuthBlocked: no arranque a frio (zero
      // contas), a primeira pessoa a entrar via Authentik também dá
      // `no_account` — mas aqui o passo certo é criar a conta em /setup,
      // não mostrar a página de erro.
      return (
        <Routes>
          <Route path="/setup" element={<Setup />} />
          <Route path="*" element={<Navigate to="/setup" replace />} />
        </Routes>
      )
    }
    if (forwardAuthBlocked) {
      return <ForwardAuthBlocked reason={forwardAuthBlocked.reason} email={forwardAuthBlocked.email} />
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
      <Route path="/colecoes" element={<Cookbooks />} />
      <Route path="/colecoes/:id" element={<CookbookDetail />} />
      <Route path="/despensa" element={<Pantry />} />
      <Route path="/login" element={<Navigate to="/" replace />} />
      <Route path="/setup" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
