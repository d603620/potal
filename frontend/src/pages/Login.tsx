import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const [userId, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // すでにログイン済みならログイン画面をスキップ
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      const from =
        (location.state as any)?.from?.pathname || '/dashboard';
      navigate(from, { replace: true });
    }
  }, [navigate, location]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // クライアント側の必須チェック（APIを叩く前）
    if (!userId || !password) {
      setError('社員IDとパスワードを入力してください。');
      return;
    }

    setSubmitting(true);

    try {
      const resp = await fetch('auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          employee_id: userId,
          password: password,
        }),
      });

      if (!resp.ok) {
        if (resp.status === 401) {
          setError('社員IDまたはパスワードが正しくありません。');
        } else {
          setError(
            'ログインに失敗しました。しばらくしてから再度お試しください。'
          );
        }
        return;
      }

      const data = await resp.json();

      // トークンとユーザー情報を保存
      localStorage.setItem('token', data.token);
      if (data.user) {
        localStorage.setItem(
          'employeeId',
          data.user.employee_id ?? userId
        );
        if (data.user.name) {
          localStorage.setItem('userName', data.user.name);
        }
      }

      // ログイン前にアクセスしようとしていたページがあればそこへ
      const from =
        (location.state as any)?.from?.pathname || '/dashboard';
      navigate(from, { replace: true });
    } catch (e) {
      console.error(e);
      setError(
        'ネットワークエラーが発生しました。しばらくしてから再度お試しください。'
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white shadow-xl rounded-xl p-8">
        <h1 className="text-xl font-bold text-[#003E7E] mb-6">
          DENG1G Portal ログイン
        </h1>

        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-1">
            <label className="text-sm">社員ID</label>
            <input
              className="
                bg-white text-black 
                border border-gray-300 
                rounded-md px-3 py-2 
                focus:border-[#005BAC] focus:outline-none 
                placeholder:text-gray-400
              "
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-sm">パスワード</label>
            <input
              type="password"
              className="
                bg-white text-black 
                border border-gray-300 
                rounded-md px-3 py-2 
                focus:border-[#005BAC] focus:outline-none 
                placeholder:text-gray-400
              "
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 mt-1">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="mt-4 bg-[#005BAC] text-white py-2 rounded-full hover:bg-[#003E7E] disabled:opacity-60"
            disabled={submitting}
          >
            {submitting ? 'ログイン中…' : 'ログイン'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Login;
