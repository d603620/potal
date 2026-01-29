// frontend/src/pages/Profile.tsx
import { useEffect, useState } from "react"

type User = {
  employee_id: string
  name?: string | null
}

export default function Profile() {
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    const token = localStorage.getItem("token")
    if (!token) return

    fetch("http://10.178.7.4:8000/api/me", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(res => {
        if (!res.ok) throw new Error("unauthorized")
        return res.json()
      })
      .then(data => setUser(data))
      .catch(() => setUser(null))
  }, [])

  return (
    <div className="dnp-page">
      <div className="kpi-hero">
        <div>
          <h2 className="kpi-hero-title">Profile</h2>

          {user ? (
            <>
              <p>社員ID: {user.employee_id}</p>
              <p>氏名: {user.name ?? "未設定"}</p>
            </>
          ) : (
            <p>ユーザー情報を取得できません。</p>
          )}
        </div>
      </div>
    </div>
  )
}
