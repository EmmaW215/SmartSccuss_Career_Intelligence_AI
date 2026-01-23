import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isPro: boolean;
  login: () => Promise<void>;
  logout: () => void;
  upgradeToPro: () => Promise<void>;
  isLoading: boolean;
  // Modal Controls
  showLoginModal: boolean;
  setShowLoginModal: (show: boolean) => void;
  showUpgradeModal: boolean;
  setShowUpgradeModal: (show: boolean) => void;
  triggerLogin: () => void;
  triggerUpgrade: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);

  // Initialize with a Guest user if nothing is found
  useEffect(() => {
    const savedUser = localStorage.getItem('ss_user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    } else {
      setUser({
        id: 'guest_123',
        name: 'Guest User',
        email: 'guest@smartsuccess.ai',
        isPro: false,
        type: 'guest'
      });
    }
  }, []);

  const login = async () => {
    setIsLoading(true);
    // Simulate Google Login popup delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    const newUser: User = {
      id: 'user_google_789',
      name: 'Alex Johnson',
      email: 'alex.j@gmail.com',
      avatar: 'AJ',
      isPro: false, // Default to free tier on login
      type: 'registered'
    };
    
    setUser(newUser);
    localStorage.setItem('ss_user', JSON.stringify(newUser));
    setIsLoading(false);
    setShowLoginModal(false); // Close modal on success
  };

  const logout = () => {
    const guestUser: User = {
      id: 'guest_123',
      name: 'Guest User',
      email: 'guest@smartsuccess.ai',
      isPro: false,
      type: 'guest'
    };
    setUser(guestUser);
    localStorage.removeItem('ss_user');
  };

  const upgradeToPro = async () => {
    if (!user) return;
    setIsLoading(true);
    await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate Stripe processing
    
    const proUser: User = { ...user, isPro: true };
    setUser(proUser);
    localStorage.setItem('ss_user', JSON.stringify(proUser));
    setIsLoading(false);
    setShowUpgradeModal(false);
  };

  const triggerLogin = () => setShowLoginModal(true);
  const triggerUpgrade = () => setShowUpgradeModal(true);

  return (
    <AuthContext.Provider value={{ 
      user, 
      isAuthenticated: user?.type === 'registered', 
      isPro: user?.isPro || false,
      login, 
      logout,
      upgradeToPro,
      isLoading,
      showLoginModal,
      setShowLoginModal,
      showUpgradeModal,
      setShowUpgradeModal,
      triggerLogin,
      triggerUpgrade
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};