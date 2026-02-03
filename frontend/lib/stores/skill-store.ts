/**
 * 技能管理状态 Store
 */

import { create } from "zustand";
import {
  listSkills,
  getSkill,
  createSkill as apiCreateSkill,
  updateSkill as apiUpdateSkill,
  deleteSkill as apiDeleteSkill,
  type Skill,
  type SkillCreate,
  type SkillUpdate,
  type SkillType,
} from "@/lib/api/skills";

type FilterType = "all" | "system" | "document" | "custom";

interface SkillState {
  // 数据
  skills: Skill[];
  selectedSkill: Skill | null;
  filterType: FilterType;

  // 加载状态
  isLoading: boolean;
  isSaving: boolean;

  // Actions
  loadSkills: (type?: string) => Promise<void>;
  selectSkill: (skill: Skill | null) => void;
  setFilterType: (type: FilterType) => void;
  createSkill: (data: SkillCreate) => Promise<Skill | null>;
  updateSkill: (id: string, data: SkillUpdate) => Promise<boolean>;
  deleteSkill: (id: string) => Promise<boolean>;
  toggleSkillActive: (id: string) => Promise<boolean>;
  refreshSkill: (id: string) => Promise<void>;
  reset: () => void;
}

export const useSkillStore = create<SkillState>()((set, get) => ({
  skills: [],
  selectedSkill: null,
  filterType: "all",
  isLoading: false,
  isSaving: false,

  loadSkills: async (type?: string) => {
    set({ isLoading: true });
    try {
      const filterType = type || get().filterType;
      const skillType = filterType === "all" ? undefined : (filterType as SkillType);
      const res = await listSkills({ type: skillType });
      set({ skills: res.items, isLoading: false });
    } catch (error) {
      console.error("加载技能失败:", error);
      set({ isLoading: false });
    }
  },

  selectSkill: (skill: Skill | null) => {
    set({ selectedSkill: skill });
  },

  setFilterType: (type: FilterType) => {
    set({ filterType: type });
    get().loadSkills(type);
  },

  createSkill: async (data: SkillCreate) => {
    set({ isSaving: true });
    try {
      const skill = await apiCreateSkill(data);
      set((state) => ({
        skills: [skill, ...state.skills],
        isSaving: false,
      }));
      return skill;
    } catch (error) {
      console.error("创建技能失败:", error);
      set({ isSaving: false });
      return null;
    }
  },

  updateSkill: async (id: string, data: SkillUpdate) => {
    set({ isSaving: true });
    try {
      const updated = await apiUpdateSkill(id, data);
      set((state) => ({
        skills: state.skills.map((s) => (s.id === id ? updated : s)),
        selectedSkill:
          state.selectedSkill?.id === id ? updated : state.selectedSkill,
        isSaving: false,
      }));
      return true;
    } catch (error) {
      console.error("更新技能失败:", error);
      set({ isSaving: false });
      return false;
    }
  },

  deleteSkill: async (id: string) => {
    try {
      await apiDeleteSkill(id);
      set((state) => ({
        skills: state.skills.filter((s) => s.id !== id),
        selectedSkill:
          state.selectedSkill?.id === id ? null : state.selectedSkill,
      }));
      return true;
    } catch (error) {
      console.error("删除技能失败:", error);
      return false;
    }
  },

  toggleSkillActive: async (id: string) => {
    const skill = get().skills.find((s) => s.id === id);
    if (!skill) return false;

    return get().updateSkill(id, { is_active: !skill.is_active });
  },

  refreshSkill: async (id: string) => {
    try {
      const skill = await getSkill(id);
      if (skill) {
        set((state) => ({
          skills: state.skills.map((s) => (s.id === id ? skill : s)),
          selectedSkill:
            state.selectedSkill?.id === id ? skill : state.selectedSkill,
        }));
      }
    } catch (error) {
      console.error("刷新技能失败:", error);
    }
  },

  reset: () => {
    set({
      skills: [],
      selectedSkill: null,
      filterType: "all",
      isLoading: false,
      isSaving: false,
    });
  },
}));
