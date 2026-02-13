import { useEffect } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../firebase';
import { MessageHandler } from '../types';

export function useParentMessage(handlers: MessageHandler) {
  useEffect(() => {
    const allowedOrigins = [
      'https://smart-success-ai.vercel.app',
      'http://localhost:3000',
    ];

    const handleMessage = (event: MessageEvent) => {
      if (!allowedOrigins.includes(event.origin) && import.meta.env.PROD) {
        return;
      }

      switch (event.data.action) {
        case 'showLoginModal':
          handlers.showLoginModal?.(event.data.message);
          break;

        case 'getLoginStatus':
          const user = auth.currentUser;
          if (event.source && event.source !== window) {
            (event.source as Window).postMessage(
              {
                type: 'loginStatus',
                isLoggedIn: !!user,
                userInfo: user
                  ? {
                      uid: user.uid,
                      displayName: user.displayName,
                      email: user.email,
                      photoURL: user.photoURL,
                    }
                  : null,
              },
              event.origin
            );
          }
          break;

        case 'hideVisitorCounter':
          handlers.hideVisitorCounter?.();
          break;
      }
    };

    window.addEventListener('message', handleMessage);

    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage(
          {
            type: 'loginStatus',
            isLoggedIn: !!user,
            userInfo: user
              ? {
                  uid: user.uid,
                  displayName: user.displayName,
                  email: user.email,
                  photoURL: user.photoURL,
                }
              : null,
          },
          '*'
        );

        if (user) {
          window.parent.postMessage(
            {
              type: 'loginSuccess',
              userInfo: {
                uid: user.uid,
                displayName: user.displayName,
                email: user.email,
                photoURL: user.photoURL,
              },
            },
            '*'
          );
        }
      }
    });

    return () => {
      window.removeEventListener('message', handleMessage);
      unsubscribe();
    };
  }, [handlers]);
}
