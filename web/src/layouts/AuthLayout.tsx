import { Outlet } from "react-router-dom";

export function AuthLayout() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 p-4">
      <div className="w-full max-w-5xl flex flex-col lg:flex-row bg-white rounded-3xl shadow-xl overflow-hidden min-h-[560px]">
        <div className="flex-1 flex items-center justify-center p-8 md:p-12">
          <div className="w-full max-w-sm">
            <Outlet />
          </div>
        </div>

        <div className="hidden lg:flex flex-1 items-center justify-center bg-gradient-to-br from-[#FF5B8F] via-rose-300 to-orange-400 p-8">
          <img
            src="/login-image.png"
            alt="Ilustração"
            className="w-full max-w-sm h-auto object-contain drop-shadow-xl"
          />
        </div>
      </div>
    </div>
  );
}
