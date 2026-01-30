import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import LicenseCheckerPage from "./pages/LicenseCheckerPage";


function App() {
  const navigate = useNavigate()
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'))

  useEffect(() => {
    if (!token) navigate('/login')
  }, [token, navigate])

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#005BAC] text-white">
      {/* ===== ヘッダー ===== */}
      <header className="bg-[#005BAC] shadow-md">
        <div className="max-w-8xl mx-auto px-6 py-3 flex items-center gap-6">
          <h1 className="text-xl font-semibold tracking-wide">
            DENG1 Portal
          </h1>

          <nav className="flex items-center gap-4 ml-6 text-sm">
            <Link to="/dashboard" className="hover:bg-white/20 rounded-full px-3 py-1">
              ダッシュボード
            </Link>
            <Link to="/chatpod" className="hover:bg-white/20 rounded-full px-3 py-1">
              ChatBOT
            </Link>
            <Link to="/filejson" className="hover:bg-white/20 rounded-full px-3 py-1">
              JSONツール
            </Link>
            <Link to="/profile" className="hover:bg-white/20 rounded-full px-3 py-1">
              プロフィール
            </Link>
            <Link to="/trouble/search" className="hover:bg-white/20 rounded-full px-3 py-1">
              トラブル検索
            </Link>
            {/* ★ 追加 */}
            <Link to="/trouble/tacit" className="hover:bg-white/20 rounded-full px-3 py-1">
              暗黙知承認
            </Link>
            <Link to="/kpi/analyzer" className="hover:bg-white/20 rounded-full px-3 py-1">
              生産計画KPI分析
            </Link>
            <Link to="/edu-demo" className="hover:bg-white/20 rounded-full px-3 py-1">
              教育資料作成デモ
            </Link>
            <Link to="/license-checker" className="hover:bg-white/20 rounded-full px-3 py-1">
              ライセンスチェッカー
            </Link>
            <Link to="/oracle-nlq" className="hover:bg-white/20 rounded-full px-3 py-1">
              Oracle NLQ
            </Link>
            <Link to="/clothing" className="hover:bg-white/20 rounded-full px-3 py-1">
              お天気服装アドバイス
            </Link>
          </nav>


          <div className="ml-auto">
            {token && (
              <button
                onClick={logout}
                className="border border-white px-3 py-1 rounded-full hover:bg-white hover:text-[#005BAC] transition"
              >
                ログアウト
              </button>
            )}
          </div>
        </div>
      </header>

      {/* ===== ページ本体 ===== */}
      <main className="flex-1 max-w-8xl mx-auto px-6 py-6 text-black">
        <Outlet />
      </main>

      {/* ===== フッター ===== */}
      <footer className="max-w-8xl mx-auto px-6 py-4 text-xs text-white/70">
        © Dai Nippon Printing Co., Ltd.
      </footer>
    </div>
  )
}

export default App
