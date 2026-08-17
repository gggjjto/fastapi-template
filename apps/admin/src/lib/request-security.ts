export const cookieOptions = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax" as const,
  path: "/api",
};

export function isSameOrigin(requestUrl: string, origin: string | null): boolean {
  return origin === new URL(requestUrl).origin;
}
